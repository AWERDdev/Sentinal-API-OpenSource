import logging

from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse

# Import your local configuration and modules
from config import ratelimiter
from logger_config.logs_handler import setupLogger
from routes.canary_generation import router as canary_generation_router  
from routes.canary_fetching import router as canary_featch_router      
from routes.canary_trigger import router as canary_trigger_router        
from routes.canary_delete import router as canary_delete_router

# 1. Initialization
setupLogger()
logger = logging.getLogger("app")

app = FastAPI()

# 2. Register Routers
app.include_router(canary_generation_router)
app.include_router(canary_featch_router)
app.include_router(canary_trigger_router)
app.include_router(canary_delete_router)


# 3. Main Endpoints
@app.get('/', dependencies=[Depends(ratelimiter)])
def welcome_message(request: Request):
    """Root health check for the Canary API."""
    logger.info("API Root endpoint has been called")
    
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        html_content = """
        <!DOCTYPE html>
        <html>
            <head>
                <title>Canary Token Generator API</title>
                <style>
                    body { 
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                        background-color: #f4f6f9; 
                        color: #333; 
                        margin: 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        box-sizing: border-box;
                        padding: 20px;
                    }
                    .container { 
                        width: 100%;
                        max-width: 600px; 
                        background: white; 
                        padding: 30px; 
                        border-radius: 8px;  
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
                    }
                    h1 { color: #2c3e50; }
                    p { font-size: 1.1em; color: #555; }
                    .footer { margin-top: 20px; font-size: 0.8em; color: #888; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Welcome to Canary Token Generator API 🛡️</h1>
                    <p>Your API Gateway is up and running smoothly.</p>
                    <p>Use the navigation to check out the documentation or integrate your endpoints.</p>
                    <div class="footer">Status: Operational</div>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=200)

    return {"message": "welcome to canary token generator API", "status":200}


@app.get('/canary/docs', dependencies=[Depends(ratelimiter)])
def canary_docs(request: Request):
    """Example endpoint for documentation access."""
    logger.info("canary DOCS have been called")
    git_repo = "https://github.com/AWERDdev/sentinel-api"
    
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        html_content = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>Canary API - Documentation</title>
                <style>
                    body {{ 
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                        background-color: #f4f6f9; 
                        color: #333; 
                        margin: 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        box-sizing: border-box;
                        padding: 20px;
                    }}
                    .container {{ 
                        width: 100%;
                        max-width: 600px; 
                        background: white; 
                        padding: 30px; 
                        border-radius: 8px;  
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
                    }}
                    h1 {{ color: #2980b9; }}
                    p {{ font-size: 1.1em; color: #555; }}
                    a {{ color: #3498db; text-decoration: none; font-weight: bold; }}
                    a:hover {{ text-decoration: underline; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Documentation Hub</h1>
                    <p>Docs endpoint reached successfully.</p>
                    <p>📦 <strong>Git Repository:</strong> <a href="{git_repo}" target="_blank">{git_repo}</a></p>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=200)
                            
    return {"message": "Docs endpoint reached", "GitRepo": git_repo}

# uvicorn main:app --reload