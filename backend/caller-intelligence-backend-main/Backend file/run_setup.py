#!/usr/bin/env python3
"""
Complete setup script for Call Management System
Run this to set up everything from scratch
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and print output"""
    print(f"\n{'='*60}")
    print(f"📦 {description}")
    print(f"{'='*60}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False
    print(result.stdout)
    return True

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     Call Management System - Complete Setup Script       ║
    ║                                                          ║
    ║  This script will:                                       ║
    ║  1. Install required packages                            ║
    ║  2. Setup PostgreSQL database                            ║
    ║  3. Create tables and import data                        ║
    ║  4. Start the FastAPI server                             ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    # Step 1: Install packages
    if not run_command("pip install fastapi uvicorn sqlalchemy psycopg2-binary python-multipart pandas phonenumbers", 
                       "Installing Python packages"):
        print("Failed to install packages. Please install manually.")
        return
    
    # Step 2: Create database tables and import data
    if not run_command("python create_tables.py", 
                       "Creating database tables and importing data"):
        print("Failed to setup database. Please check your PostgreSQL connection.")
        return
    
    # Step 3: Start the server
    print("\n" + "="*60)
    print("🚀 Starting FastAPI Server...")
    print("="*60)
    print("\nYour API will be available at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop the server\n")
    
    subprocess.run("uvicorn main:app --host 0.0.0.0 --port 8000 --reload", shell=True)

if __name__ == "__main__":
    main()