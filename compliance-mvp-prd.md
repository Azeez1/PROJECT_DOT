# DOT Fleet Compliance Report Generator - PRD

**Project:** Automated Compliance Snapshot Generator  
**Platform:** Replit  
**Output:** 6-7 Page Branded PDF Report  
**Date:** June 21, 2025  

## 1. Project Goal
Build a web app that generates professional DOT compliance reports identical to the provided sample format. Users upload 7 data files and receive a 6-7 page branded PDF (1 visual dashboard + 5-6 pages of detailed analysis) in minutes instead of hours.

## 2. Exact Report Format (6-7 Pages Total)

### Page 1: Visual Dashboard
**Layout:** 
- **Header:** [COMPANY NAME] | DOT Fleet | Compliance Snapshot | [Date Range]
- **Left Column (30%):** Summary text with key metrics
- **Right Column (70%):** 6 data visualizations in dark containers
- **Background:** Company equipment/site photo (blurred/watermarked)

**Required Visualizations:**
1. **Fleet Score Gauge**
   - Semi-circular gauge (0-100)
   - Shows Corporate, GL, OV, SE scores
   - Target line at 90
   - Current score prominently displayed

2. **HOS Violations Bar Chart**
   - Stacked bars by region (GL, OV, SE)
   - Color-coded violation types
   - Total count displayed

3. **HOS 4-Week Trend**
   - Line graph with 4 trend lines
   - Weekly data points
   - Legend for violation types

4. **Safety Events Bar Chart**
   - Grouped by region
   - Event types in legend
   - Total events count

5. **Unassigned Driving Segments**
   - Visual representation (icons or bars)
   - Driver names and counts
   - Total segments highlighted

6. **Speeding Events Pie Chart**
   - 4 severity levels (Light, Moderate, Heavy, Severe)
   - Percentages shown
   - Total count displayed

### Pages 2-6: Detailed Narrative Report

**Page 2: Overview and HOS Analysis**
- Header with company logo and report details
- DOT Fleet Safety Snapshot introduction
- Overall Fleet Safety Summary (full paragraph)
- HOS Violations Summary with:
  - Total violations and trend
  - Regional breakdown with numbers
  - Week-over-week comparison
  - Top violation types with counts
  - Detailed insights paragraph

**Page 3: Trends and Safety Events**
- HOS Violation Trend (4 weeks) analysis
- Detailed trend insights
- Safety Inbox Events Analysis:
  - Total events and dismissals
  - Regional breakdown
  - Event type breakdown
  - Full insights paragraph

**Page 4: Personal Conveyance**
- PC Usage guidelines and goals
- Detailed table of drivers exceeding limits
- Analysis notes and observations
- Total PC time calculations

**Page 5: Unassigned Driving & Speeding**
- Unassigned Driving Segments:
  - Visual chart/graph
  - Detailed insights
  - Table with specific vehicles/drivers
- Driver Behavior & Speeding Analysis:
  - Event counts by severity
  - Regional breakdown
  - Insights and recommendations

**Page 6: DVIRs and Risk Assessment**
- Missed DVIRs table (Pre/Post Trip)
- Driver-by-driver breakdown
- Overall DOT Risk Assessment:
  - Comprehensive multi-paragraph analysis
  - Risk factors summary
  - Compliance recommendations
  - Action items

**Page 7 (if needed): Appendix**
- Individuals Contacted list (numbered)
- Additional data tables
- Supplementary information

## 3. Data Input Files (7 CSV/Excel)

1. **fleet_scores.csv**
   ```
   Region, Score, Previous_Score
   Corporate, 91, 97
   Great Lakes, 91, 89
   Ohio Valley, 95, 95
   Southeast, 93, 96
   ```

2. **hos_violations.csv**
   ```
   Region, Missing_Cert, Shift_Duty, Shift_Driving, Cycle_Limit, Rest_Break
   GL, 75, 20, 3, 0, 10
   OV, 30, 15, 2, 0, 3
   SE, 77, 29, 2, 0, 0
   ```

3. **safety_events.csv**
   ```
   Region, Following_Distance, Harsh_Turn, Harsh_Brake, Defensive_Driving
   Corporate, 5, 0, 0, 0
   GL, 4, 0, 0, 0
   SE, 3, 0, 1, 0
   ```

4. **unassigned_driving.csv**
   ```
   Vehicle_ID, Driver_Name, Segments, Duration
   ST-B1665, Logan Eaves, 25, 86:00:32
   MV-18270, Richard Rivera, 2, 10:21:15
   ```

5. **speeding_events.csv**
   ```
   Driver_Name, Light, Moderate, Heavy, Severe
   Various, 27, 3, 0, 8
   ```

6. **personal_conveyance.csv**
   ```
   Driver_Name, PC_Duration
   Johnny Halderman, 27:01:13
   Roberto Garcia, 18:42:27
   Adam Watson, 12:59:31
   ```

7. **missed_dvirs.csv**
   ```
   Driver_Name, Post_Trip, Pre_Trip
   Adam Watson, 7, 7
   Bobby Delancey, 5, 5
   Caleb Newton, 5, 5
   ```

## 4. Technical Implementation

### Technical Implementation:
```python
# main.py structure
app = Flask(__name__)

@app.route('/')
def upload_page():
    # Simple upload form with 7 file inputs
    
@app.route('/generate', methods=['POST'])
def generate_report():
    # 1. Process uploaded files
    # 2. Generate visualizations for Page 1
    # 3. Create PDF with ReportLab:
    #    - Page 1: Visual dashboard
    #    - Pages 2-6: Narrative sections
    #    - Page 7: Appendix (if needed)
    # 4. Return PDF download
    
def create_pdf():
    # Use ReportLab to create multi-page document
    # Page 1: Add charts as images
    # Pages 2-6: Format text, tables, analysis
    # Maintain consistent headers/footers
```

### Key Libraries:
- **matplotlib** - Charts with custom styling
- **reportlab** - PDF generation
- **pandas** - Data processing
- **Pillow** - Image handling

### Color Palette:
```python
COLORS = {
    'primary_blue': '#1E4D8B',
    'background_dark': '#2C2C2C',
    'accent_orange': '#F57C00',
    'success_green': '#4CAF50',
    'warning_yellow': '#FFC107',
    'light_gray': '#E0E0E0'
}
```

## 5. Customization Points

User can configure:
- Company name
- Company logo
- Background image for Page 1
- Target safety score (default: 90)
- Date ranges
- Region names

## 6. MVP Features

**Included:**
- Upload 7 CSV/Excel files
- Generate all 6 visualizations for page 1
- Create 5-6 pages of formatted narrative analysis
- Produce complete 6-7 page PDF matching sample
- Professional tables and text formatting
- Download completed report
- Basic error handling
- Placeholder company branding

**Not Included (Phase 2):**
- SAMSARA API integration
- Automated scheduling
- Email delivery
- User accounts
- Historical reports
- Real-time data updates

## 7. Success Metrics

- ✅ PDF matches sample format exactly (all 6-7 pages)
- ✅ Page 1 visual dashboard renders all 6 charts correctly
- ✅ Pages 2-6 narrative flows properly with correct formatting
- ✅ All tables format with proper alignment
- ✅ Process completes in < 60 seconds
- ✅ Handles missing data gracefully
- ✅ Works on Replit free tier
- ✅ PDF is readable on all devices

## 8. Development Timeline

**Week 1:**
- Day 1-2: Replit setup, file upload interface
- Day 3-4: Data processing for all 7 files
- Day 5: Create first 3 visualizations

**Week 2:**
- Day 1-2: Complete remaining visualizations
- Day 3: Page 1 visual dashboard layout
- Day 4-5: Pages 2-6 narrative formatting

**Week 3:**
- Day 1-2: Tables and data formatting
- Day 3: Multi-page PDF composition
- Day 4-5: Testing and deployment

## 9. Testing Requirements

- Test with incomplete data files
- Verify calculations match manual process
- Ensure PDF renders on different devices
- Validate all visualizations are readable
- Check narrative text formatting

## 10. Deployment

```
# Replit deployment
1. Upload code to Replit
2. Install dependencies
3. Set environment variables
4. Configure custom domain (optional)
5. Share link with compliance team
```

## 11. Future Enhancements

1. **SAMSARA Integration** - Direct API pulls
2. **Scheduling** - Automated weekly generation
3. **Distribution** - Email reports to stakeholders
4. **Archive** - Store historical reports
5. **Comparisons** - Month-over-month analysis
6. **Alerts** - Notify when scores drop