# Pattern Detection Ideas for Community Statistics

## Overview

This document explores ideas for implementing lightweight pattern detection in our community statistics system to identify significant patterns in record and usage delta/snapshot data.

## Current Statistics Foundation

Our system already tracks rich time-series data:

### Record Statistics
- **Daily deltas**: Changes in record counts, file counts, data volume, unique uploaders
- **Daily snapshots**: Cumulative totals at specific points in time
- **Subcounts by**: resource type, access status, language, affiliations, funders, subjects, publishers, periodicals, file types

### Usage Statistics  
- **Daily deltas**: Daily view/download counts with unique visitors, records, files
- **Daily snapshots**: Cumulative usage totals
- **Subcounts by**: All record metadata fields plus referrers and visitor countries

## Pattern Detection Approaches

### 1. Simple Statistical Analysis
- **Moving averages** to smooth daily fluctuations and identify underlying trends
- **Growth rate calculations** (week-over-week, month-over-month) for key metrics
- **Percentile analysis** to identify unusually high/low activity periods

### 2. Threshold-Based Alerts
- Set up simple rules like "if downloads increase by >50% from previous week"
- Monitor for sudden drops in activity that might indicate system issues
- Track when communities exceed their typical usage patterns

### 3. Basic Correlation Analysis
- Look for relationships between record additions and subsequent usage spikes
- Identify which communities drive global trends
- Find correlations between metadata fields (e.g., certain subjects get more downloads)

### 4. Seasonal Pattern Recognition
- Detect weekly patterns (weekday vs weekend usage)
- Identify academic calendar effects (semester starts, conference seasons)
- Track yearly patterns for grant cycles or publication seasons

### 5. Change Point Detection
- Identify when growth rates shift significantly
- Detect the impact of policy changes or major events
- Find structural breaks in usage patterns

### 6. Anomaly Detection
- Use simple z-score analysis to flag unusual spikes or drops
- Monitor for missing data or data quality issues
- Identify outliers in subcount distributions

## Implementation Strategy

Start simple and build incrementally, using existing daily aggregation data as the foundation.

## Mathematical Foundations

### 1. Moving Averages

**Simple Moving Average (SMA) - Plain English Explanation:**

Think of SMA like calculating the "average temperature over the last 7 days" - you're smoothing out daily fluctuations to see the underlying trend.

**The Math:**
```
SMA(n) = (x₁ + x₂ + ... + xₙ) / n
```

**What this actually means:**
- `x₁, x₂, x₃...` = your daily values (like daily downloads: 10, 15, 8, 12, 20...)
- `n` = how many days you want to average (like 7 days)
- You add up the last `n` values and divide by `n`

**Real Example - Step by Step:**
If your daily downloads for the last 7 days were: `[10, 15, 8, 12, 20, 18, 14]`

**Step 1:** Add all the values together
```
10 + 15 + 8 + 12 + 20 + 18 + 14 = 97
```

**Step 2:** Count how many values you have
```
We have 7 values (7 days)
```

**Step 3:** Divide the sum by the count
```
97 ÷ 7 = 13.857... ≈ 13.86
```

**Step 4:** That's your SMA!
```
7-day SMA = 13.86 downloads per day
```

**What this tells you:** Instead of seeing daily fluctuations (8 to 20), you see your "typical" daily rate is about 14 downloads.

**What Makes It "Moving"?**

The key difference between a regular average and a **moving** average is that SMA recalculates every day with the most recent data.

**Example - How SMA Moves:**

**Day 8:** You get 16 downloads
- Old data: `[10, 15, 8, 12, 20, 18, 14]` (days 1-7)
- New data: `[15, 8, 12, 20, 18, 14, 16]` (days 2-8)
- New SMA: (15+8+12+20+18+14+16) ÷ 7 = 103 ÷ 7 = 14.71

**Day 9:** You get 11 downloads  
- New data: `[8, 12, 20, 18, 14, 16, 11]` (days 3-9)
- New SMA: (8+12+20+18+14+16+11) ÷ 7 = 99 ÷ 7 = 14.14

**The "Moving" Part:** Each day, you drop the oldest day and add the newest day, then recalculate the average.

**Why This Matters:** 
- Regular average: Uses ALL your historical data (gets stale)
- Moving average: Always uses your most recent 7 days (stays current)

**Practical Application - Chart Display Option:**

You could add a toggle to your time-series charts: "Show 7-day moving average"

**How it would work:**
- User sees their daily download data as dots/points
- User clicks "Show SMA" checkbox
- Chart calculates SMA for each day and draws a smooth line
- User can see both the noisy daily data AND the underlying trend

**Example Chart Data:**
```
Day 1: 10 downloads (SMA: 10.0)
Day 2: 15 downloads (SMA: 12.5) 
Day 3: 8 downloads  (SMA: 11.0)
Day 4: 12 downloads (SMA: 11.25)
Day 5: 20 downloads (SMA: 13.0)
Day 6: 18 downloads (SMA: 13.83)
Day 7: 14 downloads (SMA: 13.86)
Day 8: 16 downloads (SMA: 14.71)
```

**What the user sees:**
- Daily dots bouncing around (10, 15, 8, 12, 20, 18, 14, 16...)
- Smooth SMA line trending upward (10.0, 12.5, 11.0, 11.25, 13.0, 13.83, 13.86, 14.71...)

**Implementation Note - Apache ECharts:**
ECharts doesn't have built-in SMA functionality, but you can:
1. **Pre-calculate SMA** in JavaScript and add as a second series
2. **Use echarts-stat extension** (`npm install echarts-stat`) for statistical functions
3. **Custom calculation** - implement SMA in your data processing layer

**Why SMA is useful:**
- **Smooths out noise**: One bad day (8 downloads) doesn't ruin your trend
- **Shows underlying pattern**: Instead of seeing daily ups and downs, you see if you're generally growing or declining
- **Reduces false alarms**: A single spike doesn't trigger alerts
- **Tracks meaningful trends**: Helps you see real changes in activity, not just random daily variation
- **Notices meaningful changes**: When SMA starts trending up or down, it's usually a real pattern worth paying attention to

**Exponential Moving Average (EMA) - The "Recent Days Matter More" Version:**
```
EMA(today) = α × value(today) + (1-α) × EMA(yesterday)
```

**Plain English:** EMA gives more weight to recent days. If α = 0.3, then today's value gets 30% weight and yesterday's EMA gets 70% weight.

**When to use which:**
- **SMA**: When all recent days are equally important
- **EMA**: When recent trends matter more than older data

### 2. Growth Rate Calculations

**What Growth Rate Means - Plain English:**
Growth rate tells you how much something increased or decreased compared to a previous period. It's like asking "How much did we grow compared to last week/month/year?"

**Week-over-Week Growth - Step by Step:**

**Real Example:** Last week you had 100 downloads, this week you have 120 downloads.

**Step 1:** Calculate the difference
```
Current Week - Previous Week = 120 - 100 = 20
```

**Step 2:** Divide by the previous week's value
```
20 ÷ 100 = 0.20
```

**Step 3:** Multiply by 100 to get percentage
```
0.20 × 100 = 20%
```

**Result:** You grew by 20% week-over-week!

**The Formula:**
```
Growth Rate = (Current Week - Previous Week) / Previous Week × 100%
```

**What This Tells You:**
- **Positive growth** (like +20%): Things are getting better
- **Negative growth** (like -15%): Things are declining  
- **Zero growth** (0%): Things stayed the same

**Practical Application - Growth Rate Chart Display:**

You could add a "Show Growth Rate" option to your charts that calculates week-over-week or month-over-month growth.

**How it would work:**
- User sees their daily data (downloads, views, etc.)
- User clicks "Show Growth Rate" 
- Chart calculates growth rate for each period and displays as a line
- User can see both absolute numbers AND growth trends

**Example Chart Data:**
```
Week 1: 100 downloads (Growth Rate: --)
Week 2: 120 downloads (Growth Rate: +20%)
Week 3: 110 downloads (Growth Rate: -8.3%)
Week 4: 130 downloads (Growth Rate: +18.2%)
Week 5: 140 downloads (Growth Rate: +7.7%)
```

**What the user sees:**
- Primary chart: Absolute numbers (100, 120, 110, 130, 140...)
- Secondary chart: Growth rates (--, +20%, -8.3%, +18.2%, +7.7%)
- User can spot: "Oh, we had a dip in week 3, but recovered in week 4"

### 3. Percentile Analysis  
*(We'll cover this after you understand SMA)*

## Implementation Questions

**Data Source for Calculations:**
- **Delta series**: Daily changes (good for spotting daily anomalies)
- **Snapshot series**: Cumulative totals (good for overall trends)
- **Combined approach**: Use both depending on what you're analyzing

**Recommendation:**
- **SMA**: Use delta series for daily activity trends
- **Growth Rate**: Use snapshot series for overall growth trends
- **Both**: Calculate both and let users choose what to display

## Utility Functions

### JavaScript Utility Functions for Chart Data Transformation

```javascript
/**
 * Calculate Simple Moving Average for a data series
 * @param {Array} dataPoints - Array of {date, value} objects
 * @param {number} windowSize - Number of periods to average (e.g., 7 for 7-day SMA)
 * @returns {Array} Array of {date, value} objects with SMA values
 */
function calculateSMA(dataPoints, windowSize = 7) {
  if (dataPoints.length < windowSize) {
    return []; // Not enough data
  }
  
  const smaData = [];
  
  for (let i = windowSize - 1; i < dataPoints.length; i++) {
    // Get the window of data points
    const window = dataPoints.slice(i - windowSize + 1, i + 1);
    
    // Calculate average
    const sum = window.reduce((acc, point) => acc + point.value, 0);
    const average = sum / windowSize;
    
    // Use the date of the last point in the window
    smaData.push({
      date: dataPoints[i].date,
      value: average
    });
  }
  
  return smaData;
}

/**
 * Calculate growth rate between consecutive periods
 * @param {Array} dataPoints - Array of {date, value} objects
 * @param {string} periodType - 'daily', 'weekly', 'monthly'
 * @returns {Array} Array of {date, value} objects with growth rates
 */
function calculateGrowthRate(dataPoints, periodType = 'weekly') {
  if (dataPoints.length < 2) {
    return [];
  }
  
  const growthData = [];
  
  for (let i = 1; i < dataPoints.length; i++) {
    const current = dataPoints[i].value;
    const previous = dataPoints[i - 1].value;
    
    if (previous === 0) {
      // Avoid division by zero
      growthData.push({
        date: dataPoints[i].date,
        value: null // or 0, depending on how you want to handle this
      });
    } else {
      const growthRate = ((current - previous) / previous) * 100;
      growthData.push({
        date: dataPoints[i].date,
        value: growthRate
      });
    }
  }
  
  return growthData;
}

/**
 * Transform data series to show SMA instead of raw data
 * @param {Array} dataSeriesArray - Array of data series objects (each with a `data` property)
 * @param {number} windowSize - Number of periods to average (e.g., 7 for 7-day SMA)
 * @returns {Array} Data series array with SMA data points
 */
function transformToSMA(dataSeriesArray, windowSize = 7) {
  return dataSeriesArray.map(series => ({
    ...series,
    data: calculateSMA(series.data, windowSize)
  }));
}

/**
 * Transform data series to show growth rates instead of raw data
 * @param {Array} dataSeriesArray - Array of data series objects (each with a `data` property)
 * @returns {Array} Data series array with growth rate data points
 */
function transformToGrowthRate(dataSeriesArray) {
  return dataSeriesArray.map(series => ({
    ...series,
    data: calculateGrowthRate(series.data)
  }));
}

/**
 * Usage example:
 * 
 * // Original data series array
 * const dataSeriesArray = [
 *   { name: "Community A", data: [{date: "2024-01-01", value: 10}, ...] },
 *   { name: "Community B", data: [{date: "2024-01-01", value: 15}, ...] }
 * ];
 * 
 * // Transform to show SMA
 * const smaSeries = transformToSMA(dataSeriesArray, 7);
 * 
 * // Transform to show growth rates
 * const growthSeries = transformToGrowthRate(dataSeriesArray);
 * 
 * // Pass the transformed series to your chart component
 */
```

## Available Tools

### Python Tools

**Moving Averages:**
- **Built-in**: Simple list comprehensions and `statistics.mean()`
- **NumPy**: `numpy.convolve()` for SMA, `pandas.ewm()` for EMA
- **Pandas**: `Series.rolling().mean()` for SMA, `Series.ewm()` for EMA

**Growth Rates:**
- **Built-in**: Simple arithmetic operations
- **Pandas**: `Series.pct_change()` for percentage changes
- **NumPy**: `numpy.diff()` for differences

**Percentiles:**
- **Built-in**: `statistics.quantiles()` (Python 3.8+)
- **NumPy**: `numpy.percentile()`, `numpy.quantile()`
- **Pandas**: `Series.quantile()`, `Series.describe()`
- **SciPy**: `scipy.stats.percentileofscore()`

### JavaScript Tools

**Moving Averages:**
- **Built-in**: Array methods like `reduce()` and `slice()`
- **D3.js**: `d3.rollup()` for grouping and averaging
- **SimpleMath.js**: Custom implementations

**Growth Rates:**
- **Built-in**: Simple arithmetic operations
- **Custom functions**: Easy to implement with array methods

**Percentiles:**
- **Built-in**: Array sorting and indexing
- **D3.js**: `d3.quantile()` for percentile calculations
- **Simple-statistics**: `ss.quantile()`, `ss.iqr()`

## Implementation Examples

### Python Example (Moving Average)
```python
import statistics
from collections import deque

def simple_moving_average(data, window_size):
    """Calculate simple moving average"""
    if len(data) < window_size:
        return None
    
    return statistics.mean(data[-window_size:])

def exponential_moving_average(data, alpha=0.3):
    """Calculate exponential moving average"""
    if not data:
        return None
    
    ema = data[0]
    for value in data[1:]:
        ema = alpha * value + (1 - alpha) * ema
    
    return ema
```

### JavaScript Example (Growth Rate)
```javascript
function calculateGrowthRate(current, previous) {
    if (previous === 0) return null;
    return ((current - previous) / previous) * 100;
}

function weekOverWeekGrowth(weeklyData) {
    return weeklyData.map((week, index) => {
        if (index === 0) return null;
        return calculateGrowthRate(week.value, weeklyData[index - 1].value);
    });
}
```

## Integration with Existing Data

Our daily aggregation data is perfect for these analyses because:

1. **Time-series structure**: Daily data points with consistent intervals
2. **Multiple metrics**: Views, downloads, record counts, etc.
3. **Subcount breakdowns**: Can analyze patterns within specific categories
4. **Community-level data**: Can compare patterns across communities

## Next Steps

- [x] Understand the math behind simple statistical analysis
- [x] Identify available Python/JavaScript tools
- [ ] Design lightweight implementation approach
- [ ] Prototype with existing data
- [ ] Integrate with dashboard UI
