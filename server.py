from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from binance.client import Client
from kiteconnect import KiteConnect
from SmartApi import SmartConnect

import sqlite3

app = FastAPI()

# Connect to Binance API
def connect_to_binance(api_key: str, api_secret: str):
    try:
        client = Client(api_key, api_secret)
        account_info = client.get_account()  # This will confirm the connection
        return True, account_info
    except Exception as e:
        return False, str(e)

# Check Binance connection
@app.post("/check-binance/{id}")
async def check_binance(id: int):
    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute("SELECT api_key, api_secret FROM api_credentials WHERE id=?", (id,))
    credentials = cursor.fetchone()
    conn.close()

    if credentials:
        api_key, api_secret = credentials
        connected, response = connect_to_binance(api_key, api_secret)
        if connected:
            return RedirectResponse(url="/api/binance?message=Connection Successful", status_code=303)
        else:
            return RedirectResponse(url=f"/api/binance?message=Connection Failed: {response}", status_code=303)
    return RedirectResponse(url="/api/binance?message=API Credentials Not Found", status_code=303)

# Connect to Zerodha Kite API
def connect_to_kite(api_key: str, access_token: str):
    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
        profile = kite.profile()  # This confirms the connection
        return True, profile
    except Exception as e:
        return False, str(e)

# Check Zerodha Kite connection
@app.post("/check-kite/{id}")
async def check_kite(id: int):
    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute("SELECT api_key, access_token FROM api_credentials WHERE id=?", (id,))
    credentials = cursor.fetchone()
    conn.close()

    if credentials:
        api_key, access_token = credentials
        connected, response = connect_to_kite(api_key, access_token)
        if connected:
            return RedirectResponse(url="/api/zerodha?message=Connection Successful", status_code=303)
        else:
            return RedirectResponse(url=f"/api/zerodha?message=Connection Failed: {response}", status_code=303)
    return RedirectResponse(url="/api/zerodha?message=API Credentials Not Found", status_code=303)

# Connect to AngelOne API
def connect_to_angel(api_key: str, username: str, password: str, totp: str):
    try:
        obj = SmartConnect(api_key=api_key)
        session_data = obj.generateSession(username, password, totp)
        if session_data['status']:
            profile = obj.getProfile(session_data['data']['refreshToken'])
            return True, profile
        return False, "Login failed"
    except Exception as e:
        return False, str(e)

# Check AngelOne connection
@app.post("/check-angel/{id}")
async def check_angel(id: int):
    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute("SELECT api_key, username, password, totp FROM api_credentials WHERE id=?", (id,))
    credentials = cursor.fetchone()
    conn.close()

    if credentials:
        api_key, username, password, totp = credentials
        connected, response = connect_to_angel(api_key, username, password, totp)
        if connected:
            return RedirectResponse(url="/api/angel?message=Connection Successful", status_code=303)
        else:
            return RedirectResponse(url=f"/api/angel?message=Connection Failed: {response}", status_code=303)
    return RedirectResponse(url="/api/angel?message=API Credentials Not Found", status_code=303)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates directory
templates = Jinja2Templates(directory="templates")

# Initialize the database
def init_db():
    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        broker TEXT,
        api_key TEXT UNIQUE,
        api_secret TEXT,
        access_token TEXT,
        username TEXT,
        password TEXT,
        totp TEXT
    )
    ''')
    conn.commit()
    conn.close()

init_db()

# Fetch API data for a specific broker
def get_api_data(broker: str):
    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM api_credentials WHERE broker=?", (broker,))
    api_data = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "api_key": row[2], "api_secret": row[3], "username": row[4], "password": row[5], "totp": row[6]} for row in api_data]

# Check for duplicate entry
def is_duplicate_entry(broker: str, api_key: str):
    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM api_credentials WHERE broker=? AND api_key=?", (broker, api_key))
    duplicate = cursor.fetchone()
    conn.close()
    return duplicate is not None

# Home page
@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Delete entry
def delete_api_entry(id: int):
    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM api_credentials WHERE id=?", (id,))
    conn.commit()
    conn.close()

# Binance API Page
@app.get("/api/binance", response_class=HTMLResponse)
async def binance_page(request: Request, message: str = None):
    api_data = get_api_data("binance")
    return templates.TemplateResponse("binance_page.html", {"request": request, "api_data": api_data, "message": message})

# Zerodha Kite API Page
@app.get("/api/zerodha", response_class=HTMLResponse)
async def zerodha_page(request: Request, message: str = None):
    api_data = get_api_data("zerodha")
    return templates.TemplateResponse("zerodha_page.html", {"request": request, "api_data": api_data, "message": message})

# AngelOne API Page
@app.get("/api/angel", response_class=HTMLResponse)
async def angel_page(request: Request, message: str = None):
    api_data = get_api_data("angel")
    return templates.TemplateResponse("angel_page.html", {"request": request, "api_data": api_data, "message": message})

# Submit form for Binance with duplicate check
@app.post("/submit-binance")
async def submit_binance(binance_api_key: str = Form(...), binance_api_secret: str = Form(...)):
    if is_duplicate_entry("binance", binance_api_key):
        return RedirectResponse(url="/api/binance?message=Duplicate API Key Entry", status_code=303)

    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO api_credentials (broker, api_key, api_secret)
    VALUES ('binance', ?, ?)
    ''', (binance_api_key, binance_api_secret))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/api/binance", status_code=303)

# Submit form for Zerodha Kite with duplicate check
@app.post("/submit-kite")
async def submit_kite(kite_api_key: str = Form(...), kite_access_token: str = Form(...)):
    if is_duplicate_entry("zerodha", kite_api_key):
        return RedirectResponse(url="/api/zerodha?message=Duplicate API Key Entry", status_code=303)

    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO api_credentials (broker, api_key, access_token)
    VALUES ('zerodha', ?, ?)
    ''', (kite_api_key, kite_access_token))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/api/zerodha", status_code=303)

# Submit form for AngelOne with duplicate check
@app.post("/submit-angel")
async def submit_angel(angel_api_key: str = Form(...), angel_username: str = Form(...), angel_password: str = Form(...), angel_totp: str = Form(...)):
    if is_duplicate_entry("angel", angel_api_key):
        return RedirectResponse(url="/api/angel?message=Duplicate API Key Entry", status_code=303)

    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO api_credentials (broker, api_key, username, password, totp)
    VALUES ('angel', ?, ?, ?, ?)
    ''', (angel_api_key, angel_username, angel_password, angel_totp))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/api/angel", status_code=303)

# Delete API entries
@app.post("/delete-binance/{id}")
async def delete_binance(id: int):
    delete_api_entry(id)
    return RedirectResponse(url="/api/binance", status_code=303)

@app.post("/delete-kite/{id}")
async def delete_kite(id: int):
    delete_api_entry(id)
    return RedirectResponse(url="/api/zerodha", status_code=303)

@app.post("/delete-angel/{id}")
async def delete_angel(id: int):
    delete_api_entry(id)
    return RedirectResponse(url="/api/angel", status_code=303)

# Edit Binance
@app.get("/edit-binance/{id}", response_class=HTMLResponse)
async def edit_binance(id: int, request: Request):
    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM api_credentials WHERE id=?", (id,))
    api_entry = cursor.fetchone()
    conn.close()
    return templates.TemplateResponse("edit_binance.html", {
        "request": request, 
        "api_entry": {"id": api_entry[0], "api_key": api_entry[2], "api_secret": api_entry[3]}
    })

# Edit Zerodha
@app.get("/edit-kite/{id}", response_class=HTMLResponse)
async def edit_kite(id: int, request: Request):
    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM api_credentials WHERE id=?", (id,))
    api_entry = cursor.fetchone()
    conn.close()
    return templates.TemplateResponse("edit_kite.html", {
        "request": request, 
        "api_entry": {"id": api_entry[0], "api_key": api_entry[2], "access_token": api_entry[4]}
    })

# Edit AngelOne
@app.get("/edit-angel/{id}", response_class=HTMLResponse)
async def edit_angel(id: int, request: Request):
    conn = sqlite3.connect('api_credentials.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM api_credentials WHERE id=?", (id,))
    api_entry = cursor.fetchone()
    conn.close()
    return templates.TemplateResponse("edit_angel.html", {
        "request": request, 
        "api_entry": {"id": api_entry[0], "api_key": api_entry[2], "username": api_entry[4], "password": api_entry[5], "totp": api_entry[6]}
    })

# Check connection for Binance (mock example)
@app.post("/check-binance/{id}")
async def check_binance(id: int):
    return RedirectResponse(url="/api/binance", status_code=303)

# Check connection for Zerodha (mock example)
@app.post("/check-kite/{id}")
async def check_kite(id: int):
    return RedirectResponse(url="/api/zerodha", status_code=303)

# Check connection for AngelOne (mock example)
@app.post("/check-angel/{id}")
async def check_angel(id: int):
    return RedirectResponse(url="/api/angel", status_code=303)

@app.on_event("startup")
async def startup_event():
    print("Available routes:")
    for route in app.routes:
        print(f"Path: {route.path} - Name: {route.name}")

@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    """Render the index.html page"""
    return templates.TemplateResponse("index.html", {"request": request})
