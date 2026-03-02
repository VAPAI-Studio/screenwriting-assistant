# Screenwriter Assistant - Development Guide

## Code Standards

### Python Backend

1. **Style Guide**
   - Follow PEP 8
   - Use type hints for all functions
   - Maximum line length: 100 characters
   - Use descriptive variable names

2. **Documentation**
   - All modules must have docstrings
   - All public functions must have docstrings with:
     - Description
     - Parameters
     - Return values
     - Exceptions that may be raised

3. **Error Handling**
   - Use custom exceptions from `exceptions.py`
   - Always provide meaningful error messages
   - Log errors appropriately

4. **Testing**
   - Write unit tests for all new functions
   - Write integration tests for all API endpoints
   - Maintain test coverage above 80%

### TypeScript Frontend

1. **Style Guide**
   - Use TypeScript strict mode
   - Prefer functional components
   - Use hooks appropriately
   - Avoid `any` type

2. **Component Structure**
   - One component per file
   - Co-locate styles and tests
   - Use proper prop typing

3. **State Management**
   - Use React Query for server state
   - Use React hooks for local state
   - Avoid prop drilling

## API Development

### Adding New Endpoints

1. Create schema in `models/schemas.py`:
```python
class NewFeatureRequest(BaseModel):
    field: str = Field(..., min_length=1, max_length=100)
    
    @field_validator('field')
    def validate_field(cls, v):
        # Add validation logic
        return v
```

2. Create endpoint in appropriate file:
```python
@router.post("/new-feature", response_model=NewFeatureResponse)
async def new_feature(
    request: NewFeatureRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Document your endpoint"""
    # Implementation
```

3. Add validation in `utils/validators.py` if needed
4. Add tests in `tests/test_api.py`
5. Update API documentation

## Database Changes

### Adding New Tables

1. Update `models/database.py`:
```python
class NewTable(Base):
    __tablename__ = "new_table"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Add columns
```

2. Create migration script in `migrations/`:
```sql
-- migrations/add_new_table.sql
CREATE TABLE new_table (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Add columns
);
```

3. Update schema definitions
4. Update seed data if needed

## Frontend Development

### Adding New Components

1. Create component file:
```typescript
// components/NewComponent/NewComponent.tsx
interface NewComponentProps {
  // Define props
}

export function NewComponent({ props }: NewComponentProps) {
  // Implementation
}
```

2. Add styles if needed (using Tailwind)
3. Add tests
4. Update parent components

### Adding New Pages

1. Create page component
2. Add route in `App.tsx`
3. Update navigation if needed
4. Add data fetching with React Query

## Testing

### Backend Tests

Run all tests:
```bash
cd backend
pytest
```

Run specific test file:
```bash
pytest tests/test_validators.py
```

Run with coverage:
```bash
pytest --cov=app tests/
```

### Frontend Tests

Run all tests:
```bash
cd frontend
npm test
```

Run with coverage:
```bash
npm test -- --coverage
```

## Performance Considerations

1. **Database Queries**
   - Use eager loading to avoid N+1 queries
   - Add appropriate indexes
   - Use query optimization techniques

2. **API Responses**
   - Implement pagination for list endpoints
   - Use response caching where appropriate
   - Minimize response payload size

3. **Frontend**
   - Implement code splitting
   - Use React.memo for expensive components
   - Optimize re-renders

## Security Best Practices

1. **Input Validation**
   - Validate all user input
   - Sanitize HTML content
   - Use parameterized queries

2. **Authentication**
   - Use secure JWT tokens
   - Implement token expiration
   - Use HTTPS in production

3. **API Security**
   - Implement rate limiting
   - Use CORS appropriately
   - Validate file uploads

## Deployment

### Staging Deployment

1. Run tests
2. Build Docker images
3. Deploy to staging environment
4. Run smoke tests
5. Verify functionality

### Production Deployment

1. Create release branch
2. Run full test suite
3. Build production Docker images
4. Deploy to production
5. Monitor logs and metrics
6. Be ready to rollback if needed

## Monitoring

1. **Application Logs**
   - Monitor error rates
   - Track response times
   - Watch for unusual patterns

2. **Performance Metrics**
   - Database query performance
   - API response times
   - Frontend loading times

3. **Error Tracking**
   - Set up error reporting (e.g., Sentry)
   - Monitor error rates
   - Investigate and fix issues promptly

## Code Review Process

1. Create feature branch
2. Implement changes
3. Write/update tests
4. Update documentation
5. Create pull request
6. Address review comments
7. Merge after approval

## Release Process

1. Update version numbers
2. Update changelog
3. Create release notes
4. Tag release in git
5. Deploy to production
6. Announce release

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check DATABASE_URL
   - Verify database is running
   - Check network connectivity

2. **API Authentication Failures**
   - Verify token is valid
   - Check token expiration
   - Verify secret key configuration

3. **Frontend Build Issues**
   - Clear node_modules and reinstall
   - Check for TypeScript errors
   - Verify all dependencies are installed

### Debug Mode

Enable debug logging:
```bash
# Backend
export DEBUG=true
export LOG_LEVEL=DEBUG

# Frontend
npm run dev -- --debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Update documentation
6. Submit a pull request

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/)
- [TypeScript Documentation](https://www.typescriptlang.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
