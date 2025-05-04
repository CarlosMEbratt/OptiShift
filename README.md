# 🧠 OptiShift: Workforce Shift Optimization Tool

**OptiShift** is a Python-based scheduling tool designed to optimize shift assignments using linear programming. It ensures that workforce allocation meets operational demands while considering employee availability, preferences, and role constraints.

## 🎯 Project Objective

Create an automated scheduling solution that generates optimal weekly shift plans, reducing manual effort and ensuring fair, efficient shift coverage across the team.

## 🛠️ Technologies & Libraries

* **Python**
* **Pandas, NumPy**
* **PuLP (Linear Programming)**
* **Matplotlib (for visualization)**

## 🔧 Features

* Automatically assigns shifts to employees based on availability and required coverage.
* Ensures balanced workload distribution.
* Flexible constraint handling (max hours per employee, coverage limits, etc.).
* Easy-to-edit input files (CSV-based).

## 🔍 How It Works

1. **Input Collection**
   Users provide:

   * Employee availability matrix
   * Role requirements
   * Shift coverage needs

2. **Linear Programming Optimization**
   Using **PuLP**, the model minimizes total unmet shift requirements while respecting constraints.

3. **Output**

   * Optimized shift schedule in table format
   * Visual summaries of assignments and gaps (if any)

## 📁 Repository Structure

```
├── OptiShift.ipynb           # Main notebook with all logic, examples, and outputs
├── data/                     # Contains sample input data (availability, shift needs)
├── output/                   # Generated schedules (CSV/Excel)
└── README.md                 # Project documentation
```

## 📈 Results

* Reduced scheduling conflicts.
* Improved coverage consistency.
* Scalable for small and medium-sized teams.

## 🚀 Future Plans

* Add GUI with Streamlit for non-technical users.
* Incorporate employee preference weighting.
* Allow for multi-week/month scheduling.

