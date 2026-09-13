from fastapi import FastAPI

app = FastAPI(title="Syphership notification Service")

@app.get('/')
def root():
    return {'message': 'Notification service is running'}