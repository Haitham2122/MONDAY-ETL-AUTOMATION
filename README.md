# Monday.com GEE Integration

This project automates the workflow between Monday.com and Google Drive for document management and processing.

## Features

- PDF document processing and signing
- Integration with Monday.com API
- Google Drive file management
- Automatic folder structure creation
- Status updates in Monday.com
- Optimized PDF quality with balanced file size (approximately 2MB)
- Support for multiple Monday.com column IDs in a single endpoint

## Prerequisites

- Python 3.12
- Monday.com API key
- Google Drive API credentials

## Installation

1. Clone the repository
```bash
git clone https://github.com/Haitham2122/monday-gee-automation.git
cd monday-gee-automation
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Configure environment variables
- Set up Monday.com API key
- Configure Google Drive credentials

## Usage

Run the FastAPI application:
```bash
uvicorn app:app --reload
```

## Deployment

The application is configured for deployment on Render.com with the following specifications:
- Python 3.12 runtime
- European region (Frankfurt)
- Automatic deployment on main branch updates

## uvloop Compatibility Fix

### Problem
When deploying on Render.com, we encountered the following error with `nest_asyncio`:
```
ValueError: Can't patch loop of type <class 'uvloop.Loop'>
```

This issue occurs because Render.com uses `uvloop` with Uvicorn for better performance, but `nest_asyncio` (used in our PDF signing function) is not compatible with `uvloop`.

### Solution
1. We created `fixed_signature_utils.py` with a modified version of the `sign_pdf_bytes_visible` function.
2. The new implementation uses a separate thread with a new asyncio loop to execute PyHanko coroutines, avoiding the use of `nest_asyncio.apply()`.
3. The app.py was modified to import functions from `fixed_signature_utils.py` instead of `signature_utils.py`.

### How it works
The solution uses a design pattern that isolates asynchronous execution in a dedicated thread:

```python
def sign_pdf_bytes_visible(...):
    # Create the coroutine
    coro = _sign_pdf_bytes_visible_async(...)
    
    # Function that creates and uses a new loop in a separate thread
    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    
    # Execute in a separate thread
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_new_loop)
        return future.result()
```

This approach allows running nested asyncio code without using `nest_asyncio`, making it compatible with uvloop.

## Project Structure

```
├── app.py                    # FastAPI main application
├── signature_utils.py        # Original PDF signing utilities
├── fixed_signature_utils.py  # uvloop-compatible PDF signing utilities
├── Leyton_depot.py           # Google Drive integration
├── requirements.txt          # Project dependencies
├── render.yaml               # Render.com configuration
├── runtime.txt               # Python version specification
└── Procfile                  # Process file for deployment
```
