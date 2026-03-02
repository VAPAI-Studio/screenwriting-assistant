# backend/app/api_docs.py

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Screenwriter Assistant API",
        version="1.0.0",
        description="""
        ## Screenwriter Assistant MVP API
        
        This API helps screenwriters structure and develop scripts by providing:
        
        * **Project Management**: Create and manage screenplay projects
        * **Section Editing**: Work with story sections and plot points
        * **AI Review**: Get GPT-4 powered feedback on your writing
        * **Authentication**: Secure access with JWT tokens
        
        ### Features
        
        - Support for multiple story frameworks (Three-Act, Save the Cat, Hero's Journey)
        - Real-time content persistence
        - Section-specific checklists
        - AI-powered coherence checking
        - Keyboard shortcuts support
        
        ### Authentication
        
        All endpoints (except auth) require a Bearer token in the Authorization header:
        ```
        Authorization: Bearer <token>
        ```
        
        For development, you can use the mock token endpoint.
        """,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your bearer token"
        }
    }
    
    # Add security to all endpoints except auth
    for path in openapi_schema["paths"]:
        if not path.startswith("/api/auth"):
            for method in openapi_schema["paths"][path]:
                openapi_schema["paths"][path][method]["security"] = [{"Bearer": []}]
    
    # Add tags description
    openapi_schema["tags"] = [
        {
            "name": "auth",
            "description": "Authentication operations"
        },
        {
            "name": "projects",
            "description": "Project management operations"
        },
        {
            "name": "sections",
            "description": "Section and checklist operations"
        },
        {
            "name": "review",
            "description": "AI review operations"
        }
    ]
    
    # Add response examples
    add_response_examples(openapi_schema)
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def add_response_examples(schema):
    """Add response examples to the OpenAPI schema"""
    
    # Example project response
    project_example = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "owner_id": "123e4567-e89b-12d3-a456-426614174001",
        "title": "The Last Journey",
        "framework": "three_act",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "sections": []
    }
    
    # Example validation error response
    validation_error_example = {
        "detail": "Validation error",
        "errors": [
            {
                "field": "title",
                "message": "Title must be at least 2 characters long"
            }
        ]
    }
    
    # Add examples to components
    if "components" not in schema:
        schema["components"] = {}
    
    if "examples" not in schema["components"]:
        schema["components"]["examples"] = {}
    
    schema["components"]["examples"]["project"] = {
        "value": project_example
    }
    
    schema["components"]["examples"]["validation_error"] = {
        "value": validation_error_example
    }
    
    return schema
