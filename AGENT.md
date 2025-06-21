# AGENT.md - DOT Compliance Report Generator

## Project Overview
You are building a web application that generates DOT Fleet Compliance reports. Users upload 7 CSV/Excel files and receive a professional 6-7 page PDF report matching a specific format.

## Core Requirements

### Input: 7 Data Files
1. **fleet_scores.csv** - Regional safety scores
2. **hos_violations.csv** - Hours of Service violations
3. **safety_events.csv** - Safety incidents by type
4. **unassigned_driving.csv** - Unassigned vehicle segments
5. **speeding_events.csv** - Speeding by severity
6. **personal_conveyance.csv** - PC usage by driver
7. **missed_dvirs.csv** - Missed inspections

### Output: 6-7 Page PDF Report
- **Page 1**: Visual dashboard with 6 charts
- **Pages 2-6**: Detailed narrative analysis
- **Page 7**: Appendix (if needed)

## Technical Stack
- **Framework**: Flask (Python)
- **Platform**: Replit
- **Data Processing**: Pandas
- **Visualizations**: Matplotlib
- **PDF Generation**: ReportLab
- **Styling**: Custom blue theme (#1E4D8B)

## Implementation Guidelines

### 1. File Structure
```
/
├── app.py                 # Main Flask application
├── processors/
│   ├── __init__.py
│   ├── file_handler.py    # Handle large files & multi-sheet Excel
│   ├── fleet_scores.py    # Process safety scores
│   ├── hos_violations.py  # Process HOS data
│   ├── safety_events.py   # Process safety events
│   └── ...               # Other processors
├── visualizations/
│   ├── __init__.py
│   ├── charts.py         # All chart generation
│   └── styles.py         # Chart styling
├── pdf_generator/
│   ├── __init__.py
│   ├── page_one.py       # Visual dashboard
│   ├── narrative.py      # Pages 2-6
│   └── composer.py       # PDF assembly
├── templates/
│   └── upload.html       # Upload interface
├── static/
│   ├── style.css
│   └── placeholder_logo.png
└── requirements.txt
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
    'fleet_scores': ['Safety Scores', 'Fleet Score', 'Scores'],
    'hos_violations': ['HOS', 'Violations', 'Hours of Service'],
    'safety_events': ['Safety', 'Events', 'Incidents'],
    'unassigned': ['Unassigned', 'Unassigned Driving'],
    'speeding': ['Speeding', 'Speed Events'],
    'personal_conveyance': ['PC', 'Personal Conveyance'],
    'dvirs': ['DVIR', 'Inspections', 'Missed DVIR']
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
1. Set up Flask app with upload route
2. Create upload interface with 7 file inputs
3. Add basic file validation
4. Set up folder structure

### Phase 2: Data Processing (Day 3-4)
1. Build processors for each file type
2. Implement data validation
3. Calculate all required metrics
4. Handle edge cases
5. **Multi-source processing**:
   - Single Excel with 7 sheets
   - Mixed CSV and Excel files
   - Multiple files per data type
   - Automatic consolidation

### Excel Sheet Processing Logic
```python
def process_upload(files):
    # Check if single Excel with multiple sheets
    if len(files) == 1 and files[0].filename.endswith(('.xlsx', '.xls')):
        return process_multi_sheet_excel(files[0])
    
    # Otherwise process individual files
    else:
        return process_individual_files(files)

def process_multi_sheet_excel(excel_file):
    # Load Excel file
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
        return manual_sheet_mapping(xls, missing)
    
    return mapped_data
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

## Code Quality Standards
- Clear function names
- Comprehensive comments
- Error handling on all inputs
- Type hints where helpful
- Modular, reusable code
- **Memory optimization for Replit**:
  - Process files in chunks
  - Clear dataframes after use
  - Use generators where possible
  - Limit concurrent file processing

## Performance Optimization

### Memory Management (Replit Constraints)
```python
# Process large files efficiently
def process_large_dataset(filepath):
    # Use chunking to stay within memory limits
    chunk_size = 10000
    
    # For CSV files
    if filepath.endswith('.csv'):
        chunks = []
        for chunk in pd.read_csv(filepath, chunksize=chunk_size):
            processed = process_chunk(chunk)
            chunks.append(processed)
            del chunk  # Free memory immediately
        
        result = pd.concat(chunks, ignore_index=True)
        del chunks  # Clean up
        return result
    
    # For Excel files
    elif filepath.endswith(('.xlsx', '.xls')):
        # Use read_only mode for large files
        with pd.ExcelFile(filepath, engine='openpyxl') as xls:
            data = {}
            for sheet_name in xls.sheet_names:
                # Process one sheet at a time
                df = pd.read_excel(xls, sheet_name=sheet_name)
                data[sheet_name] = process_sheet(df)
                del df  # Free memory
            return data
```

### Upload Size Limits
- Set max file size to 100MB in Flask
- Use streaming for files over 10MB
- Show upload progress for large files
- Implement chunked file uploads if needed

## Testing Checklist
- [ ] All 7 files upload correctly
- [ ] Missing files show errors
- [ ] Charts match specifications
- [ ] PDF is exactly 6-7 pages
- [ ] Tables are properly formatted
- [ ] Narrative text is professional
- [ ] Download works across browsers
- [ ] Process completes in <60 seconds
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
- SAMSARA API integration
- Automated scheduling
- Email delivery
- Historical comparisons
- Multi-company support
- Real-time dashboards