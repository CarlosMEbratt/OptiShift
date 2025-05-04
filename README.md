# 🧠 OptiShift: Workforce Shift Optimization Tool

**OptiShift** is a Python-based scheduling solution that leverages linear programming to generate optimized shift assignments. It uses a point-based logic system to assign the most suitable employees to shifts, balancing fairness, availability, and operational requirements.

---

## 🎯 Project Objective

Develop an automated shift scheduling tool that:

* Assigns employees to roles based on their availability.
* Optimizes coverage using constraint-based logic.
* Ensures balanced workload distribution across all team members.

---

## 🛠️ Technologies Used

* **Python**
* **Pandas, NumPy**
* **PuLP (Linear Programming)**
* **Matplotlib (for visualization)**

---

## 🧮 How It Works

### 🔄 Workflow Overview

1. **Data Input**

   * Employees provide availability for each day of the week.
   * Each shift or time slot has required headcount and skill criteria.
   * A CSV matrix defines the availability of each employee.

2. **Point-Based Assignment Logic**

   * Each employee-shift combination is assigned a **score** based on:

     * **Availability** (binary: available/unavailable).
     * **Cumulative hours already assigned** (penalizes overloading).
     * **Fairness constraint** (promotes balanced distribution).
     * **Optional preferences or past assignments** (to avoid bias or repetition).
   * The optimizer **maximizes the total points** across the schedule while satisfying:

     * Minimum shift coverage.
     * Maximum hours per employee.
     * One shift per employee per day.

3. **Linear Programming (LP) Optimization**

   * The problem is modeled using the PuLP library.
   * LP constraints ensure feasibility (e.g., availability, max shifts).
   * Objective: **maximize total points across all assignments**.

4. **Output**

   * Optimized shift schedule in table format.
   * Summary visualizations (e.g., per-employee assignments, shift coverage).

---

## 📁 Repository Structure

```
├── OptiShift.ipynb           # Main notebook with end-to-end implementation
├── data/                     # Input files (employee availability, requirements)
├── output/                   # Resulting schedules and plots
└── README.md                 # Project documentation
```

---

## 📈 Results

* Efficient coverage of all required shifts.
* Balanced workload distribution.
* High flexibility for adapting to different teams or work cycles.

---

## 🚀 Future Features

* Web-based GUI (Streamlit) for easy interaction.
* Employee preferences with scoring weights.
* Multi-role and multi-location support.

