# Notification System Test Documentation

This document provides comprehensive information about the test suite for the notification system, including test structure, execution instructions, and coverage details.

## Test Structure

The notification system test suite is organized into several test modules:

### 1. Unit Tests (`test_business_logic.py`)

Unit tests focus on testing individual components in isolation:

- **ContractExpirationCheckerTest**: Tests contract expiration detection logic
- **InvoiceOverdueCheckerTest**: Tests overdue invoice detection logic  
- **RentIncreaseCheckerTest**: Tests rent increase detection and calculation logic
- **InvoiceDueSoonCheckerTest**: Tests upcoming invoice due date detection
- **NotificationServicesTest**: Tests notification creation and management services
- **NotificationLogTest**: Tests duplicate prevention functionality
- **NotificationBatchTest**: Tests batch notification functionality

### 2. Integration Tests (`test_integration.py`)

Integration tests verify complete workflows from trigger to delivery:

- **ContractExpirationWorkflowTest**: End-to-end contract expiration notifications
- **InvoiceOverdueWorkflowTest**: End-to-end overdue invoice notifications
- **RentIncreaseWorkflowTest**: End-to-end rent increase notifications
- **InvoiceDueSoonWorkflowTest**: End-to-end due soon invoice notifications
- **EmailNotificationTest**: Email delivery integration tests
- **BatchNotificationWorkflowTest**: Batch processing workflow tests
- **CeleryTaskErrorHandlingTest**: Error handling in Celery tasks
- **NotificationSystemHealthTest**: System health and configuration tests

### 3. Legacy Tests (`tests.py`)

Original tests that focus on specific scenarios:

- Basic rent increase notification creation
- Email preference handling
- Next increase date calculation

## Test Execution

### Running All Tests

```bash
# Using Django test runner
python manage.py test user_notifications

# Using pytest
pytest user_notifications/

# Using custom test runner
python user_notifications/test_runner.py
```

### Running Specific Test Categories

```bash
# Unit tests only
python user_notifications/test_runner.py --unit-only

# Integration tests only  
python user_notifications/test_runner.py --integration-only

# With coverage reporting
python user_notifications/test_runner.py --coverage
```

### Running Specific Test Classes

```bash
# Specific test class
python user_notifications/test_runner.py --test-class user_notifications.test_business_logic.ContractExpirationCheckerTest

# Specific test method
python manage.py test user_notifications.test_business_logic.ContractExpirationCheckerTest.test_get_expiring_contracts_30_days
```

### Using Pytest

```bash
# All tests with verbose output
pytest user_notifications/ -v

# Unit tests only
pytest user_notifications/test_business_logic.py -v

# Integration tests only
pytest user_notifications/test_integration.py -v

# Tests with specific marker
pytest user_notifications/ -m "unit" -v

# With coverage
pytest user_notifications/ --cov=user_notifications --cov-report=html
```

## Test Configuration

### Django Settings

Tests use specific settings for optimal test execution:

- **Database**: In-memory SQLite for speed
- **Email Backend**: `locmem` backend for email testing
- **Celery**: Eager execution for synchronous testing
- **Logging**: Console output for debugging

### Test Mixins and Utilities

The `NotificationTestMixin` class provides common utilities:

- `create_test_agent()`: Create test agent instances
- `create_test_customer()`: Create test customer instances
- `create_test_property()`: Create test property instances
- `create_test_contract()`: Create test contract instances
- `create_test_invoice()`: Create test invoice instances
- `create_test_preferences()`: Create test notification preferences
- `assert_notification_created()`: Assert notifications were created
- `assert_email_sent()`: Assert emails were sent
- `assert_notification_log_created()`: Assert notification logs exist
- `assert_batch_notification_created()`: Assert batch notifications exist

## Test Coverage

The test suite provides comprehensive coverage of:

### Business Logic Coverage

- ✅ Contract expiration detection (30-day, 7-day, expired)
- ✅ Invoice overdue detection (standard, urgent, critical)
- ✅ Rent increase detection (upcoming, overdue)
- ✅ Invoice due soon detection (7-day, 3-day)
- ✅ Notification preference handling
- ✅ Duplicate prevention logic
- ✅ Batch notification scheduling
- ✅ Next increase date calculations

### Integration Coverage

- ✅ End-to-end Celery task execution
- ✅ Database transaction handling
- ✅ Email notification delivery
- ✅ Batch processing workflows
- ✅ Error handling and retry logic
- ✅ System health checks
- ✅ Configuration validation

### Edge Cases Coverage

- ✅ Missing notification preferences
- ✅ Disabled notification types
- ✅ Invalid date calculations
- ✅ Database connection errors
- ✅ Email delivery failures
- ✅ Duplicate notification prevention
- ✅ Batch scheduling edge cases

## Test Data Management

### Test Database

Tests use an in-memory SQLite database that is:

- Created fresh for each test run
- Automatically cleaned up after tests
- Isolated between test methods
- Fast for rapid test execution

### Test Data Creation

Each test creates its own test data using:

- Factory methods in test mixins
- Realistic data scenarios
- Proper foreign key relationships
- Appropriate date ranges for testing

### Data Cleanup

Test data is automatically cleaned up:

- Database is reset between tests
- Email outbox is cleared
- Notification logs are cleared
- Batch notifications are cleared

## Mocking and Patching

Tests use mocking strategically for:

### External Dependencies

- Email sending functionality
- Database connection errors
- Celery task execution
- Invoice balance calculations

### Time-Dependent Logic

- Current date/time for consistent testing
- Date calculations for predictable results
- Scheduling logic for batch notifications

### Example Mocking Patterns

```python
# Mock email sending
@patch('user_notifications.services.send_mail')
def test_email_notification(self, mock_send_mail):
    # Test email notification logic
    pass

# Mock current date
@patch('user_notifications.checkers.timezone.now')
def test_date_calculation(self, mock_now):
    mock_now.return_value = datetime(2024, 1, 15)
    # Test date-dependent logic
    pass

# Mock database errors
@patch('user_notifications.checkers.Contract.objects.filter')
def test_database_error_handling(self, mock_filter):
    mock_filter.side_effect = DatabaseError("Connection failed")
    # Test error handling
    pass
```

## Performance Considerations

### Test Execution Speed

- In-memory database for fast I/O
- Minimal test data creation
- Efficient query patterns
- Parallel test execution support

### Memory Usage

- Automatic cleanup between tests
- Limited test data scope
- Efficient object creation
- Garbage collection friendly

### CI/CD Integration

Tests are designed for continuous integration:

- Deterministic results
- No external dependencies
- Fast execution time
- Clear failure reporting

## Debugging Tests

### Verbose Output

```bash
# Django test runner with verbose output
python manage.py test user_notifications --verbosity=2

# Pytest with verbose output
pytest user_notifications/ -v -s
```

### Debug Mode

```bash
# Run specific test with debugging
python manage.py test user_notifications.test_business_logic.ContractExpirationCheckerTest.test_get_expiring_contracts_30_days --debug-mode
```

### Logging

Tests include comprehensive logging:

- Test execution progress
- Business logic decisions
- Error conditions
- Performance metrics

## Continuous Integration

### GitHub Actions Example

```yaml
name: Notification System Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install coverage pytest-django
    
    - name: Run tests with coverage
      run: |
        python user_notifications/test_runner.py --coverage
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v1
```

### Test Quality Metrics

The test suite maintains high quality standards:

- **Coverage**: >95% line coverage
- **Assertions**: Multiple assertions per test
- **Documentation**: Comprehensive docstrings
- **Maintainability**: Clear test structure
- **Reliability**: Consistent test results

## Troubleshooting

### Common Issues

1. **Database Migration Errors**
   - Solution: Use `--nomigrations` flag or ensure migrations are up to date

2. **Email Backend Errors**
   - Solution: Verify `EMAIL_BACKEND` setting in test configuration

3. **Celery Task Errors**
   - Solution: Ensure `CELERY_TASK_ALWAYS_EAGER = True` in test settings

4. **Import Errors**
   - Solution: Check `DJANGO_SETTINGS_MODULE` environment variable

5. **Date/Time Issues**
   - Solution: Use timezone-aware datetime objects and proper mocking

### Getting Help

For test-related issues:

1. Check test output for specific error messages
2. Review test documentation and examples
3. Verify test environment configuration
4. Run tests with increased verbosity
5. Check for recent changes in test dependencies

## Future Enhancements

Planned improvements to the test suite:

- **Performance Tests**: Load testing for high-volume scenarios
- **Security Tests**: Input validation and authorization testing
- **Accessibility Tests**: UI component accessibility validation
- **API Tests**: REST API endpoint testing
- **Mobile Tests**: Mobile-specific notification testing