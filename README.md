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

## 📊 Required Data Files

You'll need to upload 7 CSV or Excel files containing your fleet data. 

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
- Fleet/Safety Scores → `fleet_scores`
- HOS/Violations → `hos_violations`
- Safety/Events/Incidents → `safety_events`
- Unassigned Driving → `unassigned_driving`
- Speeding/Speed Events → `speeding_events`
- PC/Personal Conveyance → `personal_conveyance`
- DVIR/Inspections → `missed_dvirs`

### 1. Fleet Scores (`fleet_scores.csv`)
Regional safety scores for your fleet divisions.
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

### 2. HOS Violations (`hos_violations.csv`)
Hours of Service violations by type and region.
```csv
Region,Missing_Cert,Shift_Duty,Shift_Driving,Cycle_Limit,Rest_Break
GL,75,20,3,0,10
OV,30,15,2,0,3
SE,77,29,2,0,0
```

### 3. Safety Events (`safety_events.csv`)
Safety incidents categorized by type and region.
```csv
Region,Following_Distance,Harsh_Turn,Harsh_Brake,Defensive_Driving,Dismissed
Corporate,5,0,0,0,5
GL,4,0,0,0,4
SE,3,0,1,0,4
```

### 4. Unassigned Driving (`unassigned_driving.csv`)
Vehicle segments not assigned to specific drivers.
```csv
Vehicle_ID,Driver_Name,Segments,Duration
ST-B1665,Logan Eaves,25,86:00:32
MV-18270,Richard Rivera,2,10:21:15
```

### 5. Speeding Events (`speeding_events.csv`)
Speeding incidents by severity level.
```csv
Region,Driver_Name,Light,Moderate,Heavy,Severe
GL,Various,10,1,0,5
OV,Various,8,0,0,3
SE,Various,9,2,0,8
```

### 6. Personal Conveyance (`personal_conveyance.csv`)
Personal conveyance usage by driver.
```csv
Driver_Name,PC_Duration,Days_Over_2hrs
Johnny Halderman,27:01:13,3
Roberto Garcia,18:42:27,2
Adam Watson,12:59:31,1
```

### 7. Missed DVIRs (`missed_dvirs.csv`)
Missed pre/post trip inspections by driver.
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
- **Large File Support**: Handles files up to 100MB
- **Multi-Sheet Excel**: Automatically detects and processes all sheets
- **Smart Mapping**: Auto-matches sheet names to data types
- **Professional Format**: Matches DOT compliance standards
- **Error Handling**: Clear messages for missing or incorrect data
- **Flexible Input**: Accepts both CSV and Excel files
- **Download Ready**: PDF optimized for printing and digital sharing

## 🛠️ Technical Requirements

- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection
- Data files in CSV or Excel format

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
- 🔄 SAMSARA API integration
- 📅 Automated weekly reports
- 📧 Email delivery
- 📊 Historical comparisons
- 👥 Multi-user support
- 📱 Mobile app

## 📜 License

Copyright © 2025 [Your Company Name]. All rights reserved.

---

Built with ❤️ for transportation compliance teams.