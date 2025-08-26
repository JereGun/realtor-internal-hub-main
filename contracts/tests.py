from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django import forms
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta
from contracts.models import Contract
from contracts.forms import ContractForm
from properties.models import Property
from customers.models import Customer
from agents.models import Agent


class ContractOwnerDiscountTest(TestCase):
    """
    Test cases for the owner discount functionality in the Contract model.
    Tests the owner_discount_percentage field, validation constraints, and calculation methods.
    """
    
    def setUp(self):
        """Set up test data for Contract model tests."""
        # Create test property
        self.property = Property.objects.create(
            title="Test Property",
            address="123 Test St",
            property_type="apartment",
            bedrooms=2,
            bathrooms=1,
            area=100.0,
            price=1000.00
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="123-456-7890"
        )
        
        # Create test agent
        self.agent = Agent.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="098-765-4321"
        )
        
        # Base contract data
        self.contract_data = {
            'property': self.property,
            'customer': self.customer,
            'agent': self.agent,
            'start_date': date.today(),
            'amount': Decimal('1000.00'),
            'currency': 'ARS',
            'status': Contract.STATUS_ACTIVE
        }
    
    def test_owner_discount_percentage_field_exists(self):
        """Test that the owner_discount_percentage field exists and can be set."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('10.50')
        contract.save()
        
        # Refresh from database
        contract.refresh_from_db()
        self.assertEqual(contract.owner_discount_percentage, Decimal('10.50'))
    
    def test_owner_discount_percentage_nullable(self):
        """Test that owner_discount_percentage can be null."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = None
        contract.save()
        
        contract.refresh_from_db()
        self.assertIsNone(contract.owner_discount_percentage)
    
    def test_owner_discount_percentage_blank(self):
        """Test that owner_discount_percentage can be blank."""
        contract = Contract(**self.contract_data)
        # Don't set owner_discount_percentage
        contract.save()
        
        contract.refresh_from_db()
        self.assertIsNone(contract.owner_discount_percentage)
    
    def test_owner_discount_amount_calculation(self):
        """Test owner_discount_amount method calculates correctly."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('10.00')
        contract.save()
        
        expected_discount = Decimal('1000.00') * (Decimal('10.00') / Decimal('100'))
        self.assertEqual(contract.owner_discount_amount(), Decimal('100.00'))
        self.assertEqual(contract.owner_discount_amount(), expected_discount)
    
    def test_owner_discount_amount_with_decimal_percentage(self):
        """Test owner_discount_amount with decimal percentage."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('12.50')
        contract.save()
        
        expected_discount = Decimal('1000.00') * (Decimal('12.50') / Decimal('100'))
        self.assertEqual(contract.owner_discount_amount(), Decimal('125.00'))
        self.assertEqual(contract.owner_discount_amount(), expected_discount)
    
    def test_owner_discount_amount_zero_percentage(self):
        """Test owner_discount_amount returns zero when percentage is zero."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('0.00')
        contract.save()
        
        self.assertEqual(contract.owner_discount_amount(), Decimal('0.00'))
    
    def test_owner_discount_amount_null_percentage(self):
        """Test owner_discount_amount returns zero when percentage is null."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = None
        contract.save()
        
        self.assertEqual(contract.owner_discount_amount(), Decimal('0.00'))
    
    def test_owner_discount_amount_null_amount(self):
        """Test owner_discount_amount returns zero when contract amount is null."""
        contract_data = self.contract_data.copy()
        contract_data['amount'] = None
        contract = Contract(**contract_data)
        contract.owner_discount_percentage = Decimal('10.00')
        
        self.assertEqual(contract.owner_discount_amount(), Decimal('0.00'))
    
    def test_owner_net_amount_calculation(self):
        """Test owner_net_amount method calculates correctly."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('15.00')
        contract.save()
        
        expected_net = Decimal('1000.00') - Decimal('150.00')  # 1000 - (1000 * 0.15)
        self.assertEqual(contract.owner_net_amount(), Decimal('850.00'))
        self.assertEqual(contract.owner_net_amount(), expected_net)
    
    def test_owner_net_amount_no_discount(self):
        """Test owner_net_amount equals full amount when no discount."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = None
        contract.save()
        
        self.assertEqual(contract.owner_net_amount(), Decimal('1000.00'))
    
    def test_owner_net_amount_zero_discount(self):
        """Test owner_net_amount equals full amount when discount is zero."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('0.00')
        contract.save()
        
        self.assertEqual(contract.owner_net_amount(), Decimal('1000.00'))
    
    def test_owner_net_amount_hundred_percent_discount(self):
        """Test owner_net_amount is zero when discount is 100%."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('100.00')
        contract.save()
        
        self.assertEqual(contract.owner_net_amount(), Decimal('0.00'))
    
    def test_owner_net_amount_null_amount(self):
        """Test owner_net_amount returns zero when contract amount is null."""
        contract_data = self.contract_data.copy()
        contract_data['amount'] = None
        contract = Contract(**contract_data)
        contract.owner_discount_percentage = Decimal('10.00')
        
        self.assertEqual(contract.owner_net_amount(), Decimal('0.00'))
    
    def test_valid_percentage_range_zero(self):
        """Test that 0% discount is valid."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('0.00')
        
        try:
            contract.full_clean()
            contract.save()
        except ValidationError:
            self.fail("0% discount should be valid")
    
    def test_valid_percentage_range_hundred(self):
        """Test that 100% discount is valid."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('100.00')
        
        try:
            contract.full_clean()
            contract.save()
        except ValidationError:
            self.fail("100% discount should be valid")
    
    def test_valid_percentage_range_middle(self):
        """Test that percentage in valid range is accepted."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('50.75')
        
        try:
            contract.full_clean()
            contract.save()
        except ValidationError:
            self.fail("50.75% discount should be valid")
    
    def test_invalid_negative_percentage_validation(self):
        """Test that negative percentage raises ValidationError."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('-5.00')
        
        with self.assertRaises(ValidationError) as context:
            contract.full_clean()
        
        self.assertIn('owner_discount_percentage', context.exception.message_dict)
        self.assertIn('no puede ser negativo', str(context.exception.message_dict['owner_discount_percentage']))
    
    def test_invalid_over_hundred_percentage_validation(self):
        """Test that percentage over 100% raises ValidationError."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('150.00')
        
        with self.assertRaises(ValidationError) as context:
            contract.full_clean()
        
        self.assertIn('owner_discount_percentage', context.exception.message_dict)
        self.assertIn('no puede ser mayor a 100%', str(context.exception.message_dict['owner_discount_percentage']))
    
    def test_database_constraint_negative_percentage(self):
        """Test database constraint prevents negative percentage."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('-10.00')
        
        with self.assertRaises(IntegrityError):
            contract.save()
    
    def test_database_constraint_over_hundred_percentage(self):
        """Test database constraint prevents percentage over 100%."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('200.00')
        
        with self.assertRaises(IntegrityError):
            contract.save()
    
    def test_decimal_precision_two_places(self):
        """Test that decimal precision is maintained to 2 places."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('10.55')
        contract.save()
        
        contract.refresh_from_db()
        self.assertEqual(contract.owner_discount_percentage, Decimal('10.55'))
    
    def test_max_digits_constraint(self):
        """Test that max_digits constraint is enforced (5 digits total)."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('99.99')  # 4 digits, should work
        
        try:
            contract.save()
        except Exception:
            self.fail("99.99% should be valid (4 digits)")
        
        contract.refresh_from_db()
        self.assertEqual(contract.owner_discount_percentage, Decimal('99.99'))
    
    def test_edge_case_very_small_percentage(self):
        """Test very small percentage calculations."""
        contract = Contract(**self.contract_data)
        contract.owner_discount_percentage = Decimal('0.01')  # 0.01%
        contract.save()
        
        expected_discount = Decimal('1000.00') * (Decimal('0.01') / Decimal('100'))
        self.assertEqual(contract.owner_discount_amount(), Decimal('0.10'))
        self.assertEqual(contract.owner_net_amount(), Decimal('999.90'))
    
    def test_edge_case_large_contract_amount(self):
        """Test calculations with large contract amounts."""
        contract_data = self.contract_data.copy()
        contract_data['amount'] = Decimal('999999.99')  # Large amount
        contract = Contract(**contract_data)
        contract.owner_discount_percentage = Decimal('5.00')
        contract.save()
        
        expected_discount = Decimal('999999.99') * (Decimal('5.00') / Decimal('100'))
        expected_net = Decimal('999999.99') - expected_discount
        
        self.assertEqual(contract.owner_discount_amount(), Decimal('49999.9995'))
        self.assertEqual(contract.owner_net_amount(), expected_net)
    
    def test_verbose_name_and_help_text(self):
        """Test that field has correct verbose name and help text."""
        field = Contract._meta.get_field('owner_discount_percentage')
        
        self.assertEqual(field.verbose_name, "Porcentaje de Descuento al Propietario (%)")
        self.assertEqual(field.help_text, "Porcentaje que se descontará al propietario (0-100%)")
    
    def test_field_properties(self):
        """Test field properties are correctly set."""
        field = Contract._meta.get_field('owner_discount_percentage')
        
        self.assertEqual(field.max_digits, 5)
        self.assertEqual(field.decimal_places, 2)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)


class ContractFormOwnerDiscountTest(TestCase):
    """
    Test cases for the ContractForm owner discount field validation.
    Tests form validation scenarios for the owner_discount_percentage field.
    """
    
    def setUp(self):
        """Set up test data for ContractForm tests."""
        # Create test property
        self.property = Property.objects.create(
            title="Test Property",
            address="123 Test St",
            property_type="apartment",
            bedrooms=2,
            bathrooms=1,
            area=100.0,
            price=1000.00
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="123-456-7890"
        )
        
        # Create test agent
        self.agent = Agent.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="098-765-4321"
        )
        
        # Base form data
        self.form_data = {
            'property': self.property.pk,
            'customer': self.customer.pk,
            'agent': self.agent.pk,
            'start_date': date.today().strftime('%Y-%m-%d'),
            'amount': '1000.00',
            'currency': 'ARS',
            'status': Contract.STATUS_ACTIVE
        }
    
    def test_form_includes_owner_discount_percentage_field(self):
        """Test that ContractForm includes owner_discount_percentage field."""
        form = ContractForm()
        self.assertIn('owner_discount_percentage', form.fields)
    
    def test_form_widget_configuration(self):
        """Test that owner_discount_percentage field has correct widget configuration."""
        form = ContractForm()
        field = form.fields['owner_discount_percentage']
        widget = field.widget
        
        # Check widget type
        self.assertIsInstance(widget, forms.NumberInput)
        
        # Check widget attributes
        attrs = widget.attrs
        self.assertEqual(attrs['class'], 'form-control')
        self.assertEqual(attrs['step'], '0.01')
        self.assertEqual(attrs['min'], '0')
        self.assertEqual(attrs['max'], '100')
        self.assertEqual(attrs['id'], 'id_owner_discount_percentage')
    
    def test_form_valid_with_valid_percentage(self):
        """Test form is valid with valid percentage values."""
        test_cases = ['0', '0.01', '10.50', '50.00', '99.99', '100']
        
        for percentage in test_cases:
            with self.subTest(percentage=percentage):
                form_data = self.form_data.copy()
                form_data['owner_discount_percentage'] = percentage
                form = ContractForm(data=form_data)
                
                self.assertTrue(form.is_valid(), 
                    f"Form should be valid with percentage {percentage}. Errors: {form.errors}")
    
    def test_form_valid_with_empty_percentage(self):
        """Test form is valid when owner_discount_percentage is empty."""
        form_data = self.form_data.copy()
        # Don't include owner_discount_percentage in form data
        form = ContractForm(data=form_data)
        
        self.assertTrue(form.is_valid(), 
            f"Form should be valid with empty percentage. Errors: {form.errors}")
    
    def test_form_valid_with_blank_percentage(self):
        """Test form is valid when owner_discount_percentage is blank string."""
        form_data = self.form_data.copy()
        form_data['owner_discount_percentage'] = ''
        form = ContractForm(data=form_data)
        
        self.assertTrue(form.is_valid(), 
            f"Form should be valid with blank percentage. Errors: {form.errors}")
    
    def test_form_invalid_with_negative_percentage(self):
        """Test form validation fails with negative percentage."""
        test_cases = ['-0.01', '-5.00', '-100.00']
        
        for percentage in test_cases:
            with self.subTest(percentage=percentage):
                form_data = self.form_data.copy()
                form_data['owner_discount_percentage'] = percentage
                form = ContractForm(data=form_data)
                
                self.assertFalse(form.is_valid(), 
                    f"Form should be invalid with negative percentage {percentage}")
                self.assertIn('owner_discount_percentage', form.errors)
                self.assertIn('no puede ser negativo', str(form.errors['owner_discount_percentage']))
    
    def test_form_invalid_with_over_hundred_percentage(self):
        """Test form validation fails with percentage over 100%."""
        test_cases = ['100.01', '150.00', '200.00', '999.99']
        
        for percentage in test_cases:
            with self.subTest(percentage=percentage):
                form_data = self.form_data.copy()
                form_data['owner_discount_percentage'] = percentage
                form = ContractForm(data=form_data)
                
                self.assertFalse(form.is_valid(), 
                    f"Form should be invalid with percentage over 100%: {percentage}")
                self.assertIn('owner_discount_percentage', form.errors)
                self.assertIn('no puede ser mayor a 100%', str(form.errors['owner_discount_percentage']))
    
    def test_form_invalid_with_non_numeric_percentage(self):
        """Test form validation fails with non-numeric percentage values."""
        test_cases = ['abc', 'ten', '10%', '10.5.5', 'null', 'undefined']
        
        for percentage in test_cases:
            with self.subTest(percentage=percentage):
                form_data = self.form_data.copy()
                form_data['owner_discount_percentage'] = percentage
                form = ContractForm(data=form_data)
                
                self.assertFalse(form.is_valid(), 
                    f"Form should be invalid with non-numeric percentage: {percentage}")
                self.assertIn('owner_discount_percentage', form.errors)
    
    def test_form_boundary_values(self):
        """Test form validation with boundary values."""
        # Test exact boundary values
        boundary_cases = [
            ('0', True),      # Lower boundary
            ('0.00', True),   # Lower boundary with decimals
            ('100', True),    # Upper boundary
            ('100.00', True), # Upper boundary with decimals
        ]
        
        for percentage, should_be_valid in boundary_cases:
            with self.subTest(percentage=percentage, should_be_valid=should_be_valid):
                form_data = self.form_data.copy()
                form_data['owner_discount_percentage'] = percentage
                form = ContractForm(data=form_data)
                
                if should_be_valid:
                    self.assertTrue(form.is_valid(), 
                        f"Form should be valid with boundary value {percentage}. Errors: {form.errors}")
                else:
                    self.assertFalse(form.is_valid(), 
                        f"Form should be invalid with boundary value {percentage}")
    
    def test_form_decimal_precision(self):
        """Test form handles decimal precision correctly."""
        test_cases = ['10.1', '10.12', '10.123', '10.999']
        
        for percentage in test_cases:
            with self.subTest(percentage=percentage):
                form_data = self.form_data.copy()
                form_data['owner_discount_percentage'] = percentage
                form = ContractForm(data=form_data)
                
                self.assertTrue(form.is_valid(), 
                    f"Form should be valid with decimal percentage {percentage}. Errors: {form.errors}")
    
    def test_clean_owner_discount_percentage_method(self):
        """Test the clean_owner_discount_percentage method directly."""
        form = ContractForm()
        
        # Test valid values
        valid_values = [None, Decimal('0'), Decimal('50.5'), Decimal('100')]
        for value in valid_values:
            with self.subTest(value=value):
                form.cleaned_data = {'owner_discount_percentage': value}
                result = form.clean_owner_discount_percentage()
                self.assertEqual(result, value)
        
        # Test invalid values
        invalid_values = [Decimal('-1'), Decimal('101')]
        for value in invalid_values:
            with self.subTest(value=value):
                form.cleaned_data = {'owner_discount_percentage': value}
                with self.assertRaises(forms.ValidationError):
                    form.clean_owner_discount_percentage()
    
    def test_form_save_with_owner_discount_percentage(self):
        """Test that form saves owner_discount_percentage correctly."""
        form_data = self.form_data.copy()
        form_data['owner_discount_percentage'] = '15.75'
        form = ContractForm(data=form_data)
        
        self.assertTrue(form.is_valid(), f"Form should be valid. Errors: {form.errors}")
        
        contract = form.save()
        self.assertEqual(contract.owner_discount_percentage, Decimal('15.75'))
        
        # Verify it was saved to database
        contract.refresh_from_db()
        self.assertEqual(contract.owner_discount_percentage, Decimal('15.75'))
    
    def test_form_save_without_owner_discount_percentage(self):
        """Test that form saves correctly when owner_discount_percentage is not provided."""
        form_data = self.form_data.copy()
        # Don't include owner_discount_percentage
        form = ContractForm(data=form_data)
        
        self.assertTrue(form.is_valid(), f"Form should be valid. Errors: {form.errors}")
        
        contract = form.save()
        self.assertIsNone(contract.owner_discount_percentage)
        
        # Verify it was saved to database
        contract.refresh_from_db()
        self.assertIsNone(contract.owner_discount_percentage)


class ContractDetailViewOwnerDiscountTest(TestCase):
    """
    Test cases for the contract detail view displaying owner discount information.
    Tests that discount information is properly displayed in the template.
    """
    
    def setUp(self):
        """Set up test data for contract detail view tests."""
        # Create test user for authentication
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test property
        self.property = Property.objects.create(
            title="Test Property",
            address="123 Test St",
            property_type="apartment",
            bedrooms=2,
            bathrooms=1,
            area=100.0,
            price=1000.00
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="123-456-7890"
        )
        
        # Create test agent
        self.agent = Agent.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="098-765-4321"
        )
        
        # Create client for making requests
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_contract_detail_view_displays_discount_information(self):
        """Test that contract detail view displays discount information when present."""
        # Create contract with discount
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1000.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=Decimal('15.50')
        )
        
        # Get the detail view
        url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        response = self.client.get(url)
        
        # Check response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that discount information is displayed
        self.assertContains(response, 'Descuento al Propietario')
        self.assertContains(response, '15.50%')  # Discount percentage
        self.assertContains(response, '$155')    # Discount amount (1000 * 0.155)
        self.assertContains(response, '$845')    # Net amount (1000 - 155)
        
        # Check specific elements are present
        self.assertContains(response, 'Porcentaje de Descuento:')
        self.assertContains(response, 'Monto de Descuento:')
        self.assertContains(response, 'Monto Neto del Propietario:')
    
    def test_contract_detail_view_displays_no_discount_information(self):
        """Test that contract detail view displays appropriate message when no discount."""
        # Create contract without discount
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1000.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=None
        )
        
        # Get the detail view
        url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        response = self.client.get(url)
        
        # Check response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that no discount message is displayed
        self.assertContains(response, 'Descuento al Propietario')
        self.assertContains(response, 'Sin descuento aplicado')
        self.assertContains(response, 'El propietario recibe el monto completo')
        self.assertContains(response, '$1,000')  # Full amount displayed
        
        # Check that discount-specific elements are not present
        self.assertNotContains(response, 'Porcentaje de Descuento:')
        self.assertNotContains(response, 'Monto de Descuento:')
        self.assertNotContains(response, 'Monto Neto del Propietario:')
    
    def test_contract_detail_view_displays_zero_discount(self):
        """Test that contract detail view handles zero discount correctly."""
        # Create contract with zero discount
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1000.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=Decimal('0.00')
        )
        
        # Get the detail view
        url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        response = self.client.get(url)
        
        # Check response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that discount information is displayed with zero values
        self.assertContains(response, 'Descuento al Propietario')
        self.assertContains(response, '0.00%')   # Zero discount percentage
        self.assertContains(response, '$0')      # Zero discount amount
        self.assertContains(response, '$1,000')  # Full net amount
    
    def test_contract_detail_view_displays_hundred_percent_discount(self):
        """Test that contract detail view handles 100% discount correctly."""
        # Create contract with 100% discount
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1000.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=Decimal('100.00')
        )
        
        # Get the detail view
        url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        response = self.client.get(url)
        
        # Check response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that discount information is displayed correctly
        self.assertContains(response, 'Descuento al Propietario')
        self.assertContains(response, '100.00%')  # Full discount percentage
        self.assertContains(response, '$1,000')   # Full discount amount
        self.assertContains(response, '$0')       # Zero net amount
    
    def test_contract_detail_view_displays_decimal_discount(self):
        """Test that contract detail view displays decimal discount correctly."""
        # Create contract with decimal discount
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1500.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=Decimal('12.75')
        )
        
        # Get the detail view
        url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        response = self.client.get(url)
        
        # Check response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that discount information is displayed correctly
        self.assertContains(response, 'Descuento al Propietario')
        self.assertContains(response, '12.75%')   # Decimal discount percentage
        self.assertContains(response, '$191')     # Discount amount (1500 * 0.1275 = 191.25)
        self.assertContains(response, '$1,309')   # Net amount (1500 - 191.25 = 1308.75)
    
    def test_contract_detail_view_currency_formatting(self):
        """Test that currency amounts are properly formatted with commas."""
        # Create contract with large amount
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('12500.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=Decimal('8.50')
        )
        
        # Get the detail view
        url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        response = self.client.get(url)
        
        # Check response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that amounts are formatted with commas
        self.assertContains(response, '$12,500')  # Contract amount
        self.assertContains(response, '$1,062')   # Discount amount (12500 * 0.085 = 1062.5)
        self.assertContains(response, '$11,437')  # Net amount (12500 - 1062.5 = 11437.5)
    
    def test_contract_detail_view_requires_authentication(self):
        """Test that contract detail view requires user authentication."""
        # Create contract
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1000.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=Decimal('10.00')
        )
        
        # Logout user
        self.client.logout()
        
        # Try to access detail view
        url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_contract_detail_view_context_data(self):
        """Test that contract detail view provides correct context data."""
        # Create contract with discount
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1000.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=Decimal('20.00')
        )
        
        # Get the detail view
        url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        response = self.client.get(url)
        
        # Check response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check context contains contract
        self.assertIn('contract', response.context)
        context_contract = response.context['contract']
        
        # Verify contract methods work correctly
        self.assertEqual(context_contract.owner_discount_amount(), Decimal('200.00'))
        self.assertEqual(context_contract.owner_net_amount(), Decimal('800.00'))
        self.assertEqual(context_contract.owner_discount_percentage, Decimal('20.00'))


class ContractOwnerDiscountIntegrationTest(TestCase):
    """
    Integration tests for the complete contract owner discount feature.
    Tests contract creation, editing, and end-to-end scenarios with discount functionality.
    """
    
    def setUp(self):
        """Set up test data for integration tests."""
        # Create test user for authentication
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test property
        self.property = Property.objects.create(
            title="Test Property",
            address="123 Test St",
            property_type="apartment",
            bedrooms=2,
            bathrooms=1,
            area=100.0,
            price=1000.00
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="123-456-7890"
        )
        
        # Create test agent
        self.agent = Agent.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="098-765-4321"
        )
        
        # Create client for making requests
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Base form data for contract creation
        self.contract_form_data = {
            'property': self.property.pk,
            'customer': self.customer.pk,
            'agent': self.agent.pk,
            'start_date': date.today().strftime('%Y-%m-%d'),
            'amount': '1000.00',
            'currency': 'ARS',
            'status': Contract.STATUS_ACTIVE
        }
    
    def test_create_contract_with_discount_integration(self):
        """Test complete integration flow for creating a contract with owner discount."""
        # Add discount to form data
        form_data = self.contract_form_data.copy()
        form_data['owner_discount_percentage'] = '15.50'
        
        # Submit contract creation form
        url = reverse('contracts:contract_create')
        response = self.client.post(url, data=form_data)
        
        # Should redirect to contract detail on success
        self.assertEqual(response.status_code, 302)
        
        # Verify contract was created with correct discount
        contract = Contract.objects.get(property=self.property, customer=self.customer)
        self.assertEqual(contract.owner_discount_percentage, Decimal('15.50'))
        self.assertEqual(contract.amount, Decimal('1000.00'))
        
        # Verify calculations are correct
        self.assertEqual(contract.owner_discount_amount(), Decimal('155.00'))
        self.assertEqual(contract.owner_net_amount(), Decimal('845.00'))
        
        # Follow redirect and verify detail page shows discount info
        detail_url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        detail_response = self.client.get(detail_url)
        
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, '15.50%')
        self.assertContains(detail_response, '$155')  # Discount amount
        self.assertContains(detail_response, '$845')  # Net amount
    
    def test_create_contract_without_discount_integration(self):
        """Test complete integration flow for creating a contract without owner discount."""
        # Submit contract creation form without discount
        url = reverse('contracts:contract_create')
        response = self.client.post(url, data=self.contract_form_data)
        
        # Should redirect to contract detail on success
        self.assertEqual(response.status_code, 302)
        
        # Verify contract was created without discount
        contract = Contract.objects.get(property=self.property, customer=self.customer)
        self.assertIsNone(contract.owner_discount_percentage)
        self.assertEqual(contract.amount, Decimal('1000.00'))
        
        # Verify calculations show no discount
        self.assertEqual(contract.owner_discount_amount(), Decimal('0.00'))
        self.assertEqual(contract.owner_net_amount(), Decimal('1000.00'))
        
        # Follow redirect and verify detail page shows no discount info
        detail_url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        detail_response = self.client.get(detail_url)
        
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Sin descuento aplicado')
        self.assertContains(detail_response, '$1,000')  # Full amount
    
    def test_create_contract_with_invalid_discount_integration(self):
        """Test contract creation with invalid discount values shows proper errors."""
        invalid_discount_cases = [
            ('-5.00', 'no puede ser negativo'),
            ('150.00', 'no puede ser mayor a 100%'),
            ('abc', 'Ingrese un número'),
            ('10.5.5', 'Ingrese un número'),
        ]
        
        for invalid_discount, expected_error in invalid_discount_cases:
            with self.subTest(discount=invalid_discount):
                form_data = self.contract_form_data.copy()
                form_data['owner_discount_percentage'] = invalid_discount
                
                # Submit form with invalid discount
                url = reverse('contracts:contract_create')
                response = self.client.post(url, data=form_data)
                
                # Should not redirect (form has errors)
                self.assertEqual(response.status_code, 200)
                
                # Should show form errors
                self.assertContains(response, expected_error)
                
                # Verify no contract was created
                self.assertFalse(Contract.objects.filter(
                    property=self.property, 
                    customer=self.customer
                ).exists())
    
    def test_edit_contract_add_discount_integration(self):
        """Test complete integration flow for adding discount to existing contract."""
        # Create contract without discount
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1000.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=None
        )
        
        # Prepare form data to add discount
        form_data = {
            'property': self.property.pk,
            'customer': self.customer.pk,
            'agent': self.agent.pk,
            'start_date': contract.start_date.strftime('%Y-%m-%d'),
            'amount': '1000.00',
            'currency': 'ARS',
            'status': Contract.STATUS_ACTIVE,
            'owner_discount_percentage': '12.25'
        }
        
        # Submit contract edit form
        url = reverse('contracts:contract_edit', kwargs={'pk': contract.pk})
        response = self.client.post(url, data=form_data)
        
        # Should redirect to contract detail on success
        self.assertEqual(response.status_code, 302)
        
        # Verify contract was updated with discount
        contract.refresh_from_db()
        self.assertEqual(contract.owner_discount_percentage, Decimal('12.25'))
        
        # Verify calculations are correct
        self.assertEqual(contract.owner_discount_amount(), Decimal('122.50'))
        self.assertEqual(contract.owner_net_amount(), Decimal('877.50'))
        
        # Follow redirect and verify detail page shows updated discount info
        detail_url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        detail_response = self.client.get(detail_url)
        
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, '12.25%')
        self.assertContains(detail_response, '$122')  # Discount amount
        self.assertContains(detail_response, '$877')  # Net amount
    
    def test_edit_contract_modify_discount_integration(self):
        """Test complete integration flow for modifying existing discount."""
        # Create contract with discount
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1000.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=Decimal('10.00')
        )
        
        # Prepare form data to modify discount
        form_data = {
            'property': self.property.pk,
            'customer': self.customer.pk,
            'agent': self.agent.pk,
            'start_date': contract.start_date.strftime('%Y-%m-%d'),
            'amount': '1000.00',
            'currency': 'ARS',
            'status': Contract.STATUS_ACTIVE,
            'owner_discount_percentage': '25.75'
        }
        
        # Submit contract edit form
        url = reverse('contracts:contract_edit', kwargs={'pk': contract.pk})
        response = self.client.post(url, data=form_data)
        
        # Should redirect to contract detail on success
        self.assertEqual(response.status_code, 302)
        
        # Verify contract was updated with new discount
        contract.refresh_from_db()
        self.assertEqual(contract.owner_discount_percentage, Decimal('25.75'))
        
        # Verify calculations are correct
        self.assertEqual(contract.owner_discount_amount(), Decimal('257.50'))
        self.assertEqual(contract.owner_net_amount(), Decimal('742.50'))
        
        # Follow redirect and verify detail page shows updated discount info
        detail_url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        detail_response = self.client.get(detail_url)
        
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, '25.75%')
        self.assertContains(detail_response, '$257')  # Discount amount
        self.assertContains(detail_response, '$742')  # Net amount
    
    def test_edit_contract_remove_discount_integration(self):
        """Test complete integration flow for removing discount from contract."""
        # Create contract with discount
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1000.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=Decimal('15.00')
        )
        
        # Prepare form data to remove discount (empty field)
        form_data = {
            'property': self.property.pk,
            'customer': self.customer.pk,
            'agent': self.agent.pk,
            'start_date': contract.start_date.strftime('%Y-%m-%d'),
            'amount': '1000.00',
            'currency': 'ARS',
            'status': Contract.STATUS_ACTIVE,
            'owner_discount_percentage': ''  # Empty to remove discount
        }
        
        # Submit contract edit form
        url = reverse('contracts:contract_edit', kwargs={'pk': contract.pk})
        response = self.client.post(url, data=form_data)
        
        # Should redirect to contract detail on success
        self.assertEqual(response.status_code, 302)
        
        # Verify contract discount was removed
        contract.refresh_from_db()
        self.assertIsNone(contract.owner_discount_percentage)
        
        # Verify calculations show no discount
        self.assertEqual(contract.owner_discount_amount(), Decimal('0.00'))
        self.assertEqual(contract.owner_net_amount(), Decimal('1000.00'))
        
        # Follow redirect and verify detail page shows no discount info
        detail_url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        detail_response = self.client.get(detail_url)
        
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Sin descuento aplicado')
        self.assertContains(detail_response, '$1,000')  # Full amount
    
    def test_edit_contract_with_invalid_discount_integration(self):
        """Test contract editing with invalid discount values shows proper errors."""
        # Create existing contract
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1000.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=Decimal('10.00')
        )
        
        invalid_discount_cases = [
            ('-10.00', 'no puede ser negativo'),
            ('200.00', 'no puede ser mayor a 100%'),
            ('invalid', 'Ingrese un número'),
        ]
        
        for invalid_discount, expected_error in invalid_discount_cases:
            with self.subTest(discount=invalid_discount):
                form_data = {
                    'property': self.property.pk,
                    'customer': self.customer.pk,
                    'agent': self.agent.pk,
                    'start_date': contract.start_date.strftime('%Y-%m-%d'),
                    'amount': '1000.00',
                    'currency': 'ARS',
                    'status': Contract.STATUS_ACTIVE,
                    'owner_discount_percentage': invalid_discount
                }
                
                # Submit form with invalid discount
                url = reverse('contracts:contract_edit', kwargs={'pk': contract.pk})
                response = self.client.post(url, data=form_data)
                
                # Should not redirect (form has errors)
                self.assertEqual(response.status_code, 200)
                
                # Should show form errors
                self.assertContains(response, expected_error)
                
                # Verify contract was not modified
                contract.refresh_from_db()
                self.assertEqual(contract.owner_discount_percentage, Decimal('10.00'))
    
    def test_contract_amount_change_with_discount_integration(self):
        """Test that changing contract amount updates discount calculations correctly."""
        # Create contract with discount
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            start_date=date.today(),
            amount=Decimal('1000.00'),
            currency='ARS',
            status=Contract.STATUS_ACTIVE,
            owner_discount_percentage=Decimal('20.00')
        )
        
        # Verify initial calculations
        self.assertEqual(contract.owner_discount_amount(), Decimal('200.00'))
        self.assertEqual(contract.owner_net_amount(), Decimal('800.00'))
        
        # Prepare form data to change amount
        form_data = {
            'property': self.property.pk,
            'customer': self.customer.pk,
            'agent': self.agent.pk,
            'start_date': contract.start_date.strftime('%Y-%m-%d'),
            'amount': '1500.00',  # Changed amount
            'currency': 'ARS',
            'status': Contract.STATUS_ACTIVE,
            'owner_discount_percentage': '20.00'  # Same discount percentage
        }
        
        # Submit contract edit form
        url = reverse('contracts:contract_edit', kwargs={'pk': contract.pk})
        response = self.client.post(url, data=form_data)
        
        # Should redirect to contract detail on success
        self.assertEqual(response.status_code, 302)
        
        # Verify contract was updated
        contract.refresh_from_db()
        self.assertEqual(contract.amount, Decimal('1500.00'))
        self.assertEqual(contract.owner_discount_percentage, Decimal('20.00'))
        
        # Verify calculations updated correctly
        self.assertEqual(contract.owner_discount_amount(), Decimal('300.00'))  # 1500 * 0.20
        self.assertEqual(contract.owner_net_amount(), Decimal('1200.00'))      # 1500 - 300
        
        # Follow redirect and verify detail page shows updated calculations
        detail_url = reverse('contracts:contract_detail', kwargs={'pk': contract.pk})
        detail_response = self.client.get(detail_url)
        
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, '20.00%')
        self.assertContains(detail_response, '$300')   # Updated discount amount
        self.assertContains(detail_response, '$1,200') # Updated net amount


class ContractOwnerDiscountEdgeCasesTest(TestCase):
    """
    Test cases for edge cases and boundary conditions in the owner discount feature.
    Tests extreme values, precision handling, and unusual scenarios.
    """
    
    def setUp(self):
        """Set up test data for edge case tests."""
        # Create test property
        self.property = Property.objects.create(
            title="Test Property",
            address="123 Test St",
            property_type="apartment",
            bedrooms=2,
            bathrooms=1,
            area=100.0,
            price=1000.00
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="123-456-7890"
        )
        
        # Create test agent
        self.agent = Agent.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="098-765-4321"
        )
        
        # Base contract data
        self.contract_data = {
            'property': self.property,
            'customer': self.customer,
            'agent': self.agent,
            'start_date': date.today(),
            'currency': 'ARS',
            'status': Contract.STATUS_ACTIVE
        }
    
    def test_very_large_contract_amount_with_discount(self):
        """Test discount calculations with very large contract amounts."""
        contract_data = self.contract_data.copy()
        contract_data['amount'] = Decimal('999999.99')  # Maximum practical amount
        contract_data['owner_discount_percentage'] = Decimal('5.50')
        
        contract = Contract(**contract_data)
        contract.save()
        
        expected_discount = Decimal('999999.99') * (Decimal('5.50') / Decimal('100'))
        expected_net = Decimal('999999.99') - expected_discount
        
        self.assertEqual(contract.owner_discount_amount(), expected_discount)
        self.assertEqual(contract.owner_net_amount(), expected_net)
        
        # Verify precision is maintained
        self.assertIsInstance(contract.owner_discount_amount(), Decimal)
        self.assertIsInstance(contract.owner_net_amount(), Decimal)
    
    def test_very_small_contract_amount_with_discount(self):
        """Test discount calculations with very small contract amounts."""
        contract_data = self.contract_data.copy()
        contract_data['amount'] = Decimal('0.01')  # Minimum amount
        contract_data['owner_discount_percentage'] = Decimal('50.00')
        
        contract = Contract(**contract_data)
        contract.save()
        
        expected_discount = Decimal('0.01') * (Decimal('50.00') / Decimal('100'))
        expected_net = Decimal('0.01') - expected_discount
        
        self.assertEqual(contract.owner_discount_amount(), Decimal('0.005'))
        self.assertEqual(contract.owner_net_amount(), Decimal('0.005'))
    
    def test_maximum_precision_discount_percentage(self):
        """Test discount calculations with maximum decimal precision."""
        contract_data = self.contract_data.copy()
        contract_data['amount'] = Decimal('1000.00')
        contract_data['owner_discount_percentage'] = Decimal('99.99')  # Maximum percentage
        
        contract = Contract(**contract_data)
        contract.save()
        
        expected_discount = Decimal('1000.00') * (Decimal('99.99') / Decimal('100'))
        expected_net = Decimal('1000.00') - expected_discount
        
        self.assertEqual(contract.owner_discount_amount(), Decimal('999.90'))
        self.assertEqual(contract.owner_net_amount(), Decimal('0.10'))
    
    def test_minimum_precision_discount_percentage(self):
        """Test discount calculations with minimum decimal precision."""
        contract_data = self.contract_data.copy()
        contract_data['amount'] = Decimal('1000.00')
        contract_data['owner_discount_percentage'] = Decimal('0.01')  # Minimum percentage
        
        contract = Contract(**contract_data)
        contract.save()
        
        expected_discount = Decimal('1000.00') * (Decimal('0.01') / Decimal('100'))
        expected_net = Decimal('1000.00') - expected_discount
        
        self.assertEqual(contract.owner_discount_amount(), Decimal('0.10'))
        self.assertEqual(contract.owner_net_amount(), Decimal('999.90'))
    
    def test_rounding_precision_in_calculations(self):
        """Test that calculations handle rounding correctly."""
        test_cases = [
            # (amount, percentage, expected_discount, expected_net)
            (Decimal('100.00'), Decimal('33.33'), Decimal('33.33'), Decimal('66.67')),
            (Decimal('1000.00'), Decimal('66.67'), Decimal('666.70'), Decimal('333.30')),
            (Decimal('123.45'), Decimal('12.34'), Decimal('15.2337'), Decimal('108.2163')),
        ]
        
        for amount, percentage, expected_discount, expected_net in test_cases:
            with self.subTest(amount=amount, percentage=percentage):
                contract_data = self.contract_data.copy()
                contract_data['amount'] = amount
                contract_data['owner_discount_percentage'] = percentage
                
                contract = Contract(**contract_data)
                contract.save()
                
                # Allow for small rounding differences
                self.assertAlmostEqual(
                    float(contract.owner_discount_amount()), 
                    float(expected_discount), 
                    places=4
                )
                self.assertAlmostEqual(
                    float(contract.owner_net_amount()), 
                    float(expected_net), 
                    places=4
                )
    
    def test_contract_with_null_amount_and_discount(self):
        """Test behavior when contract amount is null but discount is set."""
        contract_data = self.contract_data.copy()
        contract_data['amount'] = None
        contract_data['owner_discount_percentage'] = Decimal('10.00')
        
        contract = Contract(**contract_data)
        
        # Should return zero for calculations when amount is null
        self.assertEqual(contract.owner_discount_amount(), Decimal('0.00'))
        self.assertEqual(contract.owner_net_amount(), Decimal('0.00'))
    
    def test_concurrent_contract_modifications(self):
        """Test that concurrent modifications don't cause calculation errors."""
        # Create initial contract
        contract_data = self.contract_data.copy()
        contract_data['amount'] = Decimal('1000.00')
        contract_data['owner_discount_percentage'] = Decimal('10.00')
        
        contract = Contract(**contract_data)
        contract.save()
        
        # Simulate concurrent modifications
        contract1 = Contract.objects.get(pk=contract.pk)
        contract2 = Contract.objects.get(pk=contract.pk)
        
        # Modify both instances
        contract1.owner_discount_percentage = Decimal('15.00')
        contract2.amount = Decimal('1500.00')
        
        # Save both (last one wins)
        contract1.save()
        contract2.save()
        
        # Refresh and verify final state
        contract.refresh_from_db()
        
        # Should have the amount from contract2 and original discount from database
        self.assertEqual(contract.amount, Decimal('1500.00'))
        self.assertEqual(contract.owner_discount_percentage, Decimal('10.00'))  # Original value
        
        # Calculations should work correctly
        self.assertEqual(contract.owner_discount_amount(), Decimal('150.00'))
        self.assertEqual(contract.owner_net_amount(), Decimal('1350.00'))
    
    def test_form_validation_boundary_values(self):
        """Test form validation with exact boundary values."""
        from contracts.forms import ContractForm
        
        boundary_test_cases = [
            # (percentage, should_be_valid)
            ('0', True),
            ('0.00', True),
            ('0.01', True),
            ('99.99', True),
            ('100', True),
            ('100.00', True),
            ('-0.01', False),
            ('100.01', False),
        ]
        
        base_form_data = {
            'property': self.property.pk,
            'customer': self.customer.pk,
            'agent': self.agent.pk,
            'start_date': date.today().strftime('%Y-%m-%d'),
            'amount': '1000.00',
            'currency': 'ARS',
            'status': Contract.STATUS_ACTIVE
        }
        
        for percentage, should_be_valid in boundary_test_cases:
            with self.subTest(percentage=percentage, should_be_valid=should_be_valid):
                form_data = base_form_data.copy()
                form_data['owner_discount_percentage'] = percentage
                
                form = ContractForm(data=form_data)
                
                if should_be_valid:
                    self.assertTrue(form.is_valid(), 
                        f"Form should be valid with percentage {percentage}. Errors: {form.errors}")
                else:
                    self.assertFalse(form.is_valid(), 
                        f"Form should be invalid with percentage {percentage}")
                    self.assertIn('owner_discount_percentage', form.errors)
    
    def test_database_constraint_enforcement(self):
        """Test that database constraints are properly enforced."""
        # Test negative percentage constraint
        contract_data = self.contract_data.copy()
        contract_data['amount'] = Decimal('1000.00')
        contract_data['owner_discount_percentage'] = Decimal('-5.00')
        
        contract = Contract(**contract_data)
        
        with self.assertRaises(IntegrityError):
            contract.save()
        
        # Test over 100% constraint
        contract_data['owner_discount_percentage'] = Decimal('150.00')
        contract = Contract(**contract_data)
        
        with self.assertRaises(IntegrityError):
            contract.save()
    
    def test_model_clean_validation_comprehensive(self):
        """Test comprehensive model validation through clean() method."""
        # Test valid cases pass clean()
        valid_cases = [
            None,
            Decimal('0.00'),
            Decimal('50.00'),
            Decimal('100.00'),
        ]
        
        for percentage in valid_cases:
            with self.subTest(percentage=percentage):
                contract_data = self.contract_data.copy()
                contract_data['amount'] = Decimal('1000.00')
                contract_data['owner_discount_percentage'] = percentage
                
                contract = Contract(**contract_data)
                
                try:
                    contract.full_clean()
                except ValidationError:
                    self.fail(f"Valid percentage {percentage} should not raise ValidationError")
        
        # Test invalid cases raise ValidationError
        invalid_cases = [
            Decimal('-1.00'),
            Decimal('101.00'),
        ]
        
        for percentage in invalid_cases:
            with self.subTest(percentage=percentage):
                contract_data = self.contract_data.copy()
                contract_data['amount'] = Decimal('1000.00')
                contract_data['owner_discount_percentage'] = percentage
                
                contract = Contract(**contract_data)
                
                with self.assertRaises(ValidationError) as context:
                    contract.full_clean()
                
                self.assertIn('owner_discount_percentage', context.exception.message_dict)