# Drishti — Financial Risk Dashboard

A premium financial risk monitoring dashboard built with React, Vite, and Tailwind CSS. Features interactive charts, customer deep-dive views, and a modern dark UI.

---

## Prerequisites

You need **Node.js** installed on your machine.

### Installing Node.js (Windows)

1. Go to [https://nodejs.org](https://nodejs.org)
2. Download the **LTS** version (recommended)
3. Run the installer — make sure **"Add to PATH"** is checked during installation
4. After installation, open **Command Prompt** or **PowerShell** and verify:
   ```
   node -v
   npm -v
   ```
   Both should print version numbers.

---

## Getting Started

### 1. Install Dependencies

Open a terminal in the project folder and run:

```bash
npm install
```

This will install all required packages (React, Vite, Tailwind, etc.).

### 2. Seed the Database

The app uses a local SQLite database. You need to generate it first:

```bash
cd server
npm install
node seed.js
cd ..
```

This creates the `drishti.db` file with 1000 generated customer profiles.

### 3. Start the Backend Server

In one terminal, run:

```bash
node server/index.js
```

The API server will start on **http://localhost:3001**.

### 4. Start the Frontend

In a **second terminal**, run:

```bash
npm run dev
```

The app will open at **http://localhost:5173** (Vite will show the exact URL).

---

## Project Structure

```
Drishti/
├── index.html              # Entry HTML
├── package.json            # Frontend dependencies
├── vite.config.js          # Vite configuration
├── eslint.config.js        # Linting config
├── public/                 # Static assets (logo, icons)
├── server/
│   ├── index.js            # Express API server
│   ├── db.js               # Database connection
│   ├── seed.js             # Database seeder (run once)
│   └── package.json        # Server dependencies
└── src/
    ├── main.jsx            # App entry point
    ├── App.jsx             # Router setup
    ├── App.css             # Global styles
    ├── index.css           # Tailwind imports
    ├── api.js              # API client
    ├── assets/             # SVG assets
    ├── components/         # Reusable UI components
    │   ├── BentoGrid.jsx
    │   ├── CustomerTable.jsx
    │   ├── GaugeChart.jsx
    │   ├── SearchBar.jsx
    │   ├── Sidebar.jsx
    │   ├── WalletCard.jsx
    │   └── customer/       # Customer detail tabs
    │       ├── FinancialTab.jsx
    │       ├── InterventionTab.jsx
    │       ├── ProfileTab.jsx
    │       └── TransactionsTab.jsx
    └── pages/
        ├── SegmentSelect.jsx   # Landing page
        ├── Dashboard.jsx       # Main dashboard
        └── CustomerDetail.jsx  # Customer deep-dive
```

---

## Tech Stack

- **Frontend:** React 19, Vite, Tailwind CSS v4, Framer Motion, Recharts, Lucide Icons
- **Backend:** Express.js, better-sqlite3
- **Routing:** React Router v7

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `node` not recognized | Reinstall Node.js and ensure "Add to PATH" is checked |
| Port 3001 already in use | Close other apps using that port, or change the port in `server/index.js` |
| Port 5173 already in use | Vite will auto-pick the next available port |
| Database errors | Delete `server/drishti.db` and re-run `node server/seed.js` |
