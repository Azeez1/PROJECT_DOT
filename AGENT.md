# AGENT.md - DOT Compliance Report Generator (FastAPI)

## Project Overview
You are building a FastAPI web application that generates DOT Fleet Compliance reports. Users upload 7 CSV/Excel files and receive a professional 6-7 page PDF report matching a specific format.

## Core Requirements

### Input: 7 Report Sheets
1. **Hours Of Service Violation Report**
2. **Personnel Conveyance Report**
3. **Unassigned Hours of Service Report**
4. **Safety Inbox Report**
5. **MistDVI Report**
6. **Driver Safety Behaviors Report**
7. **Drivers Safety Report**

### Output: 6-7 Page PDF Report
- **Page 1**: Visual dashboard with 6 charts
- **Pages 2-6**: Detailed narrative analysis
- **Page 7**: Appendix (if needed)

## Technical Stack
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **Platform**: Replit
- **Data Processing**: Pandas
- **Visualizations**: Matplotlib
- **PDF Generation**: ReportLab
- **Templates**: Jinja2
- **Styling**: Custom blue theme (#1E4D8B)

## Implementation Guidelines

### 1. File Structure (Exact Layout)
```
README.md
requirements.txt
compliance_snapshot/
├── app/                          # All runtime code
│   ├── __init__.py
│   ├── main.py                   # FastAPI entrypoint
│   ├── routers/
│   │   ├── __init__.py
│   │   └── upload.py             # POST /generate endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   ├── processors/           # Each CSV/XLSX handler
│   │   │   ├── __init__.py
│   │   │   ├── file_handler.py  # Multi-sheet & large file handling
│   │   │   ├── hos_violation.py
│   │   │   ├── personnel_conveyance.py
│   │   │   ├── unassigned_hos.py
│   │   │   ├── safety_inbox.py
│   │   │   ├── mistdvi.py
│   │   │   ├── driver_behaviors.py
│   │   │   └── drivers_safety.py
│   │   ├── visualizations/
│   │   │   ├── __init__.py
│   │   │   ├── charts.py        # All chart generation
│   │   │   └── styles.py        # Chart styling & colors
│   │   └── pdf_maker.py         # PDF assembly & pipeline
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Environment, paths, limits
│   │   └── utils.py             # Chunk reader, validators
│   └── templates/               # Jinja2 HTML templates
│       └── upload.html          # Drag-and-drop upload interface
├── static/                      # Optional assets (CSS, images)
│   └── style.css
├── tests/
│   ├── __init__.py
│   ├── test_processors.py
│   ├── test_charts.py
│   └── test_api.py
```

### Dependencies (requirements.txt)
```text
fastapi==0.111.*
uvicorn[standard]==0.30.*
python-multipart==0.0.9
pandas
openpyxl
matplotlib
reportlab
jinja2
Pillow
```

### File Processing Requirements

#### Large File Handling
```python
# Use chunking for files over 10MB
def process_large_file(file_path, chunk_size=10000):
    # Read CSV in chunks
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        process_chunk(chunk)
    
# For Excel files, use openpyxl with read_only mode
def process_large_excel(file_path):
    with pd.ExcelFile(file_path, engine='openpyxl') as xls:
        # List all sheet names
        sheet_names = xls.sheet_names
        
        # Process each sheet
        for sheet in sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            process_sheet_data(df, sheet)
```

#### Multi-Sheet Excel Support
- Detect all sheets in uploaded Excel files
- Allow user to map sheets to required data types
- Support these common patterns:
  - All data in one sheet with multiple tables
  - Each data type in separate sheet
  - Multiple regions/dates across sheets
  - Summary and detail sheets

#### Sheet Mapping Interface
```python
# Expected sheet patterns
SHEET_MAPPINGS = {
    'hos_violation': ['Hours Of Service Violation Report', 'HOS Violations'],
    'personnel_conveyance': ['Personnel Conveyance Report'],
    'unassigned_hos': ['Unassigned Hours of Service Report'],
    'safety_inbox': ['Safety Inbox Report'],
    'mistdvi': ['MistDVI Report', 'Missed DVIR'],
    'driver_behaviors': ['Driver Safety Behaviors Report'],
    'drivers_safety': ['Drivers Safety Report']
}
```

### 2. Chart Specifications

#### Fleet Score Gauge
- Semi-circular gauge (180°)
- Scale: 0-100
- Target line at 90
- Show 4 regional scores
- Colors: Green (>90), Yellow (80-90), Red (<80)

#### HOS Violations Stacked Bar
- X-axis: Regions (GL, OV, SE)
- Y-axis: Violation count
- Stack: Violation types
- Show totals on top

#### 4-Week Trend Line
- 4 lines for violation types
- Weekly data points
- Smooth lines with markers
- Legend outside chart area

#### Safety Events Bar
- Grouped by region
- Event types in legend
- Show dismissed vs active

#### Unassigned Driving
- Bar chart or icon visualization
- Driver names with segment counts
- Total duration displayed

#### Speeding Pie Chart
- 4 severity levels
- Show percentages
- Total count in center

### 3. Data Processing Rules

#### Fleet Scores
- Calculate week-over-week changes
- Flag scores below 90
- Identify trending regions

#### HOS Violations
- Sum by region and type
- Calculate percentage changes
- Track 4-week trends

#### Personal Conveyance
- Flag drivers over 2hr/day or 14hr/week
- Sort by highest usage
- Calculate total fleet PC time

#### Safety Events
- Separate dismissed vs active
- Group by type and region
- Calculate rates per region

### PDF Generation Pipeline
```python
# app/services/pdf_maker.py
from pathlib import Path
from typing import Dict
import pandas as pd
from .processors import file_handler
from .visualizations import charts
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

async def run_pipeline(folder: Path, output_pdf: Path):
    """Main pipeline: processors → charts → PDF."""
    try:
        # 1. Process all uploaded files
        data = await file_handler.process_uploads(folder)
        
        # 2. Validate we have all required data
        validate_data_completeness(data)
        
        # 3. Generate visualizations
        chart_paths = await generate_all_charts(data, folder)
        
        # 4. Create PDF document
        await compose_pdf(data, chart_paths, output_pdf)
        
        # 5. Clean up temp files (optional)
        cleanup_temp_files(folder, keep_pdf=True)
        
    except Exception as e:
        # Log error and create error PDF
        create_error_pdf(output_pdf, str(e))

async def generate_all_charts(data: Dict[str, pd.DataFrame], output_dir: Path) -> Dict[str, Path]:
    """Generate all 6 dashboard charts."""
    chart_paths = {}
    
    # Fleet Score Gauge
    chart_paths['fleet_score'] = await charts.create_fleet_gauge(
        data['drivers_safety'],
        output_dir / 'fleet_score.png'
    )
    
    # HOS Violations Stacked Bar
    chart_paths['hos_violation'] = await charts.create_hos_stacked_bar(
        data['hos_violation'],
        output_dir / 'hos_violation.png'
    )
    
    # 4-Week Trend Line
    chart_paths['trend'] = await charts.create_trend_chart(
        data['hos_violation'],
        output_dir / 'trend.png'
    )
    
    # Safety Events Bar
    chart_paths['driver_behaviors'] = await charts.create_safety_events_bar(
        data['driver_behaviors'],
        output_dir / 'safety_events.png'
    )
    
    # Unassigned Driving
    chart_paths['unassigned_hos'] = await charts.create_unassigned_chart(
        data['unassigned_hos'],
        output_dir / 'unassigned.png'
    )
    
    # Speeding Pie Chart
    chart_paths['mistdvi'] = await charts.create_speeding_pie(
        data['mistdvi'],
        output_dir / 'speeding.png'
    )
    
    return chart_paths
```

### 4. PDF Layout Requirements

#### Page 1 - Visual Dashboard
```python
# Layout grid
# Left column (30%): Summary text
# Right column (70%): 6 charts in 2x3 grid
# Background: Blurred image with overlay
# Header: Company name | DOT Fleet | Date range
```

#### Pages 2-6 - Narrative
```python
# Consistent header on each page
# Professional formatting
# Tables with alternating row colors
# Bullet points for key metrics
# Full paragraphs for insights
```

### 5. Error Handling
- Validate all 7 files are uploaded
- Check for required columns
- Handle missing data gracefully
- Provide clear error messages
- Allow partial report generation
- **Large file handling**:
  - Warn if file > 50MB
  - Use streaming for files > 10MB
  - Show progress bar during processing
- **Multi-sheet handling**:
  - Auto-detect sheets
  - Show sheet mapping interface
  - Validate data in each sheet

### 6. User Customization
- Company name (placeholder)
- Company logo upload
- Background image selection
- Date range specification
- Region names (if different)
- **Sheet selection** (for multi-sheet Excel files)
- **Column mapping** (if headers differ)

## Development Steps

### Phase 1: Basic Structure (Day 1-2)
1. Set up FastAPI app structure
2. Create upload interface with Jinja2 templates
3. Implement file upload endpoint with validation
4. Set up background task processing
5. Configure Uvicorn for Replit

### Phase 2: Data Processing (Day 3-4)
1. Build processors for each file type
2. Implement async file handling
3. Calculate all required metrics
4. Handle edge cases
5. **Multi-source processing**:
   - Single Excel with 7 sheets
   - Mixed CSV and Excel files
   - Multiple files per data type
   - Automatic consolidation

### Excel Sheet Processing Logic
```python
# app/services/processors/file_handler.py
import pandas as pd
from pathlib import Path
from typing import Dict, List

async def process_uploads(folder: Path) -> Dict[str, pd.DataFrame]:
    """Process uploaded files and return mapped data."""
    files = list(folder.glob("*"))
    
    # Check if single Excel with multiple sheets
    excel_files = [f for f in files if f.suffix in ['.xlsx', '.xls']]
    
    if len(files) == 1 and excel_files:
        return await process_multi_sheet_excel(excel_files[0])
    else:
        return await process_individual_files(files)

async def process_multi_sheet_excel(excel_file: Path) -> Dict[str, pd.DataFrame]:
    """Process Excel file with multiple sheets."""
    xls = pd.ExcelFile(excel_file)
    
    # Auto-map sheets to data types
    mapped_data = {}
    for sheet_name in xls.sheet_names:
        data_type = detect_data_type(sheet_name)
        if data_type:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            mapped_data[data_type] = df
    
    # Validate we have all required data
    missing = set(REQUIRED_DATA_TYPES) - set(mapped_data.keys())
    if missing:
        # Show manual mapping interface
        return await manual_sheet_mapping(xls, missing)
    
    return mapped_data

def detect_data_type(sheet_name: str) -> str:
    """Auto-detect data type from sheet name."""
    sheet_lower = sheet_name.lower()
    
    mappings = {
        'hos_violation': ['hos violation', 'hours of service violation'],
        'personnel_conveyance': ['personnel conveyance'],
        'unassigned_hos': ['unassigned hos', 'unassigned hours'],
        'safety_inbox': ['safety inbox'],
        'mistdvi': ['mistdvi', 'missed dvir'],
        'driver_behaviors': ['driver safety behaviors'],
        'drivers_safety': ['drivers safety']
    }
    
    for data_type, patterns in mappings.items():
        if any(pattern in sheet_lower for pattern in patterns):
            return data_type
    
    return None
```

### Phase 3: Visualizations (Day 5-7)
1. Create chart generation functions
2. Apply consistent styling
3. Export charts as images
4. Test with various data

### Phase 4: PDF Generation (Day 8-10)
1. Build page 1 layout
2. Create narrative templates
3. Format tables properly
4. Assemble full PDF

### Phase 5: Testing & Polish (Day 11-14)
1. Test with real data
2. Fix formatting issues
3. Add error handling
4. Deploy to Replit

## API Endpoints

FastAPI automatically generates documentation at `/docs` and `/redoc`.

### Main Endpoints:
- `GET /` - Upload form interface
- `POST /generate` - Process files and generate report
  - Accepts: `multipart/form-data` with file uploads
  - Returns: `{"ticket": "uuid", "download_url": "/download/uuid"}`
- `GET /download/{ticket}` - Download generated PDF
  - Returns: PDF file or `{"status": "processing"}`
- `GET /static/{file}` - Serve static assets

### Health Check:
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}
```

## Code Quality Standards
- Clear function names with type hints
- Comprehensive docstrings
- Error handling on all inputs
- Async/await patterns properly used
- Modular, reusable code
- **Memory optimization for Replit**:
  - Process files in chunks
  - Clear dataframes after use
  - Use generators where possible
  - Limit concurrent file processing
- **FastAPI best practices**:
  - Use Pydantic models for validation
  - Dependency injection for shared resources
  - Background tasks for long operations
  - Proper exception handlers

## Performance Optimization

### Memory Management (Replit Constraints)
```python
# app/core/utils.py
import pandas as pd
from typing import AsyncGenerator
import asyncio

async def process_large_dataset(filepath: Path):
    """Process large files efficiently with async chunking."""
    chunk_size = 10000
    
    # For CSV files
    if filepath.suffix == '.csv':
        chunks = []
        # Run CPU-bound pandas operations in thread pool
        loop = asyncio.get_event_loop()
        
        for chunk in pd.read_csv(filepath, chunksize=chunk_size):
            processed = await loop.run_in_executor(None, process_chunk, chunk)
            chunks.append(processed)
            del chunk  # Free memory immediately
        
        result = pd.concat(chunks, ignore_index=True)
        del chunks  # Clean up
        return result
    
    # For Excel files
    elif filepath.suffix in ['.xlsx', '.xls']:
        # Use read_only mode for large files
        with pd.ExcelFile(filepath, engine='openpyxl') as xls:
            data = {}
            for sheet_name in xls.sheet_names:
                # Process one sheet at a time
                df = await loop.run_in_executor(
                    None, 
                    pd.read_excel, 
                    xls, 
                    sheet_name
                )
                data[sheet_name] = await loop.run_in_executor(
                    None,
                    process_sheet,
                    df
                )
                del df  # Free memory
            return data

# app/core/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Upload limits
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_REQUEST_SIZE: int = 200 * 1024 * 1024  # 200MB total
    CHUNK_SIZE: int = 10000  # Pandas chunk size
    
    # Paths
    TEMP_DIR: str = "/tmp"
    STATIC_DIR: str = "static"
    
    # Processing
    BACKGROUND_TIMEOUT: int = 300  # 5 minutes
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### FastAPI Configuration
```python
# app/main.py additions
from .core.config import settings

# Configure max upload size
app.add_middleware(
    ContentSizeLimitMiddleware,
    max_content_size=settings.MAX_REQUEST_SIZE
)
```

## Testing Checklist
- [ ] All 7 files upload correctly
- [ ] Missing files show errors
- [ ] Charts match specifications
- [ ] PDF is exactly 6-7 pages
- [ ] Tables are properly formatted
- [ ] Narrative text is professional
- [ ] Download works across browsers
- [ ] Process completes in <60 seconds
- [ ] **FastAPI specific**:
  - [ ] Background tasks complete successfully
  - [ ] Async endpoints respond quickly
  - [ ] File uploads handle concurrent requests
  - [ ] Download endpoint returns proper status
- [ ] **Large file tests**:
  - [ ] 50MB+ Excel file processes correctly
  - [ ] Multi-sheet Excel maps properly
  - [ ] Progress indicator shows for large files
  - [ ] Memory usage stays under 512MB (Replit limit)
- [ ] **Sheet detection tests**:
  - [ ] Auto-detects common sheet names
  - [ ] Manual mapping works for unusual names
  - [ ] Handles empty sheets gracefully
  - [ ] Combines data from multiple sheets if needed

## Future Enhancements (Not in MVP)
- SAMSARA API integration (async-ready with FastAPI)
- WebSocket support for real-time progress
- Automated scheduling with Celery/Dramatiq
- Email delivery
- Historical comparisons
- Multi-company support
- Real-time dashboards
- API endpoints for external integrations
