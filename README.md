# DOT Fleet Compliance Report Generator

Generate professional DOT compliance reports in minutes instead of hours. Upload your fleet data and receive a beautifully formatted 6-7 page PDF report.

## 🚀 Quick Start

### Option 1: Single Excel File (Recommended)
1. Upload one Excel file with 7 sheets (one for each data type)
2. System auto-detects and maps sheets
3. Generate your report

### Option 2: Multiple Files
1. Upload 7 separate CSV or Excel files
2. Each file contains one data type
3. Generate your report

### Quick Process
1. Visit the app at: `[your-replit-url].repl.co`
2. Upload your data (single Excel or multiple files)
3. Click "Generate Report"
4. Download your PDF compliance report

### API Documentation
Visit `/docs` for interactive API documentation (Swagger UI) or `/redoc` for ReDoc documentation.

## 📊 Required Data Files

You'll need to upload 7 CSV or Excel files containing your fleet data.

If you prefer a single workbook, include sheets named:
"Hours Of Service Violation Report", "Personnel Conveyance Report",
"Unassigned Hours of Service Report", "Safety Inbox Report",
"MistDVI Report", "Driver Safety Behaviors Report", and
"Drivers Safety Report".

### File Format Support
- **CSV files**: Single table per file
- **Excel files (.xlsx, .xls)**: Can contain multiple sheets
- **File size**: Up to 100MB per file
- **Multiple sheets**: System will detect and let you map sheets to data types

### Multi-Sheet Excel Instructions
If your data is in a single Excel file with multiple sheets:
1. Upload the Excel file once
2. The system will show all available sheets
3. Map each sheet to the corresponding data type
4. Or upload 7 separate files (CSV or Excel)

### Sheet Naming Conventions
The system will auto-detect sheets with these common names:
 - Hours Of Service Violation Report
 - Personnel Conveyance Report
 - Unassigned Hours of Service Report
 - Safety Inbox Report
 - MistDVI Report
 - Driver Safety Behaviors Report
 - Drivers Safety Report

### 1. Hours Of Service Violation Report
Details violations of hours of service rules.
```csv
Region,Score,Previous_Score
Corporate,91,97
Great Lakes,91,89
Ohio Valley,95,95
Southeast,93,96
```

**Alternative Excel Setup**: If all your data is in one Excel file:
- Create a sheet named "Fleet Scores" or "Safety Scores"
- Include the same columns as above
- The system will auto-detect this sheet

### 2. Personnel Conveyance Report
Summarizes authorized personal conveyance use.
```csv
Region,Missing_Cert,Shift_Duty,Shift_Driving,Cycle_Limit,Rest_Break
GL,75,20,3,0,10
OV,30,15,2,0,3
SE,77,29,2,0,0
```

### 3. Unassigned Hours of Service Report
Lists unassigned HOS events that require review.
```csv
Region,Following_Distance,Harsh_Turn,Harsh_Brake,Defensive_Driving,Dismissed
Corporate,5,0,0,0,5
GL,4,0,0,0,4
SE,3,0,1,0,4
```

### 4. Safety Inbox Report
Records safety-related messages and notifications.
```csv
Vehicle_ID,Driver_Name,Segments,Duration
ST-B1665,Logan Eaves,25,86:00:32
MV-18270,Richard Rivera,2,10:21:15
```

### 5. MistDVI Report
Tracks missed DVIR submissions.
```csv
Region,Driver_Name,Light,Moderate,Heavy,Severe
GL,Various,10,1,0,5
OV,Various,8,0,0,3
SE,Various,9,2,0,8
```

### 6. Driver Safety Behaviors Report
Analyzes driver behavior metrics.
```csv
Driver_Name,PC_Duration,Days_Over_2hrs
Johnny Halderman,27:01:13,3
Roberto Garcia,18:42:27,2
Adam Watson,12:59:31,1
```

### 7. Drivers Safety Report
Overall safety scorecards for each driver.
```csv
Driver_Name,Post_Trip,Pre_Trip
Adam Watson,7,7
Bobby Delancey,5,5
Caleb Newton,5,5
```

## 📄 Report Output

Your generated report will include:

### Page 1: Visual Dashboard
- Fleet safety score gauge
- HOS violations by region
- 4-week violation trends
- Safety events breakdown
- Unassigned driving segments
- Speeding events distribution

### Pages 2-6: Detailed Analysis
- Executive summary
- HOS violation insights
- Safety event analysis
- Personal conveyance report
- Driver behavior metrics
- Risk assessment
- Action recommendations

### Page 7: Appendix
- Contacted individuals list
- Additional data tables

## 🎨 Customization

Before generating your report, you can customize:
- Company name
- Company logo
- Report date range
- Background image for visual dashboard

## ⚡ Features

- **Fast Processing**: Generate reports in under 60 seconds
- **Async Processing**: Non-blocking file uploads and PDF generation
- **Large File Support**: Handles files up to 100MB
- **Multi-Sheet Excel**: Automatically detects and processes all sheets
- **Smart Mapping**: Auto-matches sheet names to data types
- **Professional Format**: Matches DOT compliance standards
- **Error Handling**: Clear messages for missing or incorrect data
- **Flexible Input**: Accepts both CSV and Excel files
- **Background Processing**: Upload completes immediately, process in background
- **Download Ready**: PDF optimized for printing and digital sharing

## 🛠️ Technical Requirements

- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection
- Data files in CSV or Excel format

### System Architecture
- Built with FastAPI for high performance
- Async processing for large files
- Background task processing for PDFs
- Optimized for Replit deployment

## 📝 Data Format Guidelines

### General Rules
- Use headers exactly as shown in examples
- Dates in MM/DD/YYYY format
- Times in HH:MM:SS format
- No special characters in driver names
- Regions must match across all files

### Common Issues
- **Missing columns**: Ensure all required columns are present
- **Date formats**: Use consistent date formatting
- **Empty cells**: Leave blank rather than using "N/A"
- **Region names**: Must be identical across all files

## 🔒 Data Privacy

- Files are processed in memory only
- No data is stored after report generation
- Each session is isolated
- Downloads are direct from server

## 🚨 Troubleshooting

### "Missing required columns"
Check that your CSV headers match the examples exactly.

### "Invalid date format"
Ensure dates are in MM/DD/YYYY format.

### "File upload failed"
- Check file size (max 100MB)
- Ensure file is not corrupted
- Try saving as .xlsx if using old .xls format

### "Can't find data in Excel sheets"
- Check sheet names match expected patterns
- Use the manual sheet mapping option
- Ensure data starts in cell A1

### "Large file processing timeout"
- Files over 50MB may take 2-3 minutes
- Don't refresh the page during processing
- Consider splitting very large files

### "Report generation timeout"
Large datasets may take longer. Try again or reduce data size.

### "Still processing" message
- Large files are processed in the background
- Check back in 30-60 seconds
- Don't refresh during processing
- The download link will work when ready

## 📧 Support

For issues or questions:
- Check file formats match examples
- Ensure all 7 files are uploaded
- Try sample data first
- Contact: support@[your-domain].com

## 🗓️ Roadmap

### Current Version (MVP)
- ✅ Manual file upload
- ✅ PDF report generation
- ✅ Basic customization

### Planned Features
- 🔄 SAMSARA API integration (async-ready)
- 📅 Automated weekly reports
- 📧 Email delivery
- 📊 Historical comparisons
- 👥 Multi-user support
- 📱 Mobile app
- 🔌 REST API for external integrations
- 📡 WebSocket support for real-time updates

## 📜 License

Copyright © 2025 [Your Company Name]. All rights reserved.

---

Built with ❤️ for transportation compliance teams.

# Compliance Snapshot MVP
Run `pip install -r requirements.txt` and `uvicorn compliance_snapshot.app.main:app --reload`.
