#!/usr/bin/env python3
"""
Development startup script for the FastAPI backend
"""
import os
import sys
import subprocess

# Add backend directory to Python path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

def main():
    os.chdir(backend_dir)
    
    # Set development environment
    os.environ['ENVIRONMENT'] = 'development'
    os.environ['PORT'] = '8000'
    
    # Start FastAPI with hot reload
    subprocess.run([
        'uvicorn', 
        'main:app', 
        '--host', '0.0.0.0',
        '--port', '8000',
        '--reload'
    ])

if __name__ == "__main__":
    main()