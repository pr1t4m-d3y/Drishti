const db = require('./db');

const CITIES = ['Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow', 'Chandigarh', 'Indore', 'Bhopal', 'Nagpur', 'Surat'];
const LOAN_TYPES = ['Personal Loan', 'Home Loan', 'Auto Loan', 'Education Loan', 'Business Loan', 'Gold Loan'];
const GENDERS = ['Male', 'Female'];
const FIRST_NAMES_M = ['Aarav', 'Vivaan', 'Aditya', 'Vihaan', 'Arjun', 'Sai', 'Reyansh', 'Ayaan', 'Krishna', 'Ishaan', 'Shaurya', 'Atharv', 'Ansh', 'Pranav', 'Advait', 'Kabir', 'Dhruv', 'Yash', 'Rudra', 'Arnav', 'Rohan', 'Ravi', 'Amit', 'Suresh', 'Vikram', 'Rajesh', 'Arun', 'Deepak', 'Nikhil', 'Sanjay'];
const FIRST_NAMES_F = ['Aadhya', 'Ananya', 'Anika', 'Priya', 'Isha', 'Kavya', 'Myra', 'Sara', 'Riya', 'Diya', 'Nisha', 'Meera', 'Kiara', 'Tara', 'Zara', 'Neha', 'Pooja', 'Shreya', 'Divya', 'Simran', 'Kriti', 'Aisha', 'Lakshmi', 'Gayatri', 'Bhavna', 'Swati', 'Anjali', 'Sunita', 'Rekha', 'Parul'];
const LAST_NAMES = ['Sharma', 'Verma', 'Patel', 'Gupta', 'Singh', 'Kumar', 'Joshi', 'Reddy', 'Nair', 'Iyer', 'Bhat', 'Rao', 'Chopra', 'Malhotra', 'Kapoor', 'Mehta', 'Shah', 'Desai', 'Kulkarni', 'Mukherjee'];
const MERCHANTS = ['Zomato', 'Swiggy', 'Amazon', 'Flipkart', 'Myntra', 'BigBasket', 'PhonePe', 'GPay', 'Reliance Fresh', 'DMart', 'Uber', 'Ola', 'BookMyShow', 'Netflix', 'Hotstar', 'Jio', 'Airtel', 'Vodafone', 'IRCTC', 'MakeMyTrip', 'PVR Cinemas', 'Croma', 'Nykaa', 'Starbucks', 'McDonald\'s'];
const GAMBLING_MERCHANTS = ['Dream11', 'MPL', 'WinZO', 'Parimatch', 'Stake.com'];
const LENDING_APPS = ['KreditBee', 'MoneyTap', 'EarlySalary', 'CASHe', 'Navi'];
const CATEGORIES = ['Shopping', 'Food & Dining', 'Utilities', 'Transport', 'Entertainment', 'Healthcare', 'Education', 'Groceries', 'Lifestyle', 'Travel'];
const INVESTMENT_TYPES = ['Gold', 'Silver', 'ETFs', 'Mutual Funds', 'Fixed Deposits', 'PPF', 'Stocks'];

function rand(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function pick(arr) { return arr[rand(0, arr.length - 1)]; }
function round2(n) { return Math.round(n * 100) / 100; }

function generateCustomer(id) {
    const gender = pick(GENDERS);
    const firstName = gender === 'Male' ? pick(FIRST_NAMES_M) : pick(FIRST_NAMES_F);
    const lastName = pick(LAST_NAMES);
    const name = `${firstName} ${lastName}`;
    const age = rand(22, 65);
    const city = pick(CITIES);

    const income = rand(25000, 300000);
    const expenseRatio = 0.3 + Math.random() * 0.5;
    const expenses = Math.round(income * expenseRatio);

    const loanType = pick(LOAN_TYPES);
    const loanAmount = rand(50000, 5000000);
    const emiAmount = Math.round(loanAmount / rand(12, 60));
    const accountAge = rand(1, 15);

    const hasCreditCard = Math.random() < 0.21; // ~20% have credit cards
    const creditLimit = hasCreditCard ? rand(50000, 500000) : 0;
    const creditUsedPct = hasCreditCard ? (Math.random() * 0.95 + 0.05) : 0;
    const creditUsed = Math.round(creditLimit * creditUsedPct);

    const debitBalance = rand(5000, 500000);

    // Risk factors
    const hasGambling = Math.random() < 0.08;
    const hasLendingApps = Math.random() < 0.12;
    const latePayments = Math.random() < 0.18 ? rand(1, 12) : 0;
    const failedAutoDebits = Math.random() < 0.15 ? rand(1, 5) : 0;

    // EMI to Income ratio
    const emiIncomeRatio = round2((emiAmount / income) * 100);
    const creditUtilPct = hasCreditCard ? round2((creditUsed / creditLimit) * 100) : 0;

    // Risk score calculation (0-100, higher = riskier)
    let riskScore = 0;
    riskScore += emiIncomeRatio > 50 ? 25 : emiIncomeRatio > 30 ? 15 : 5;
    riskScore += creditUtilPct > 80 ? 20 : creditUtilPct > 50 ? 10 : 2;
    riskScore += latePayments * 4;
    riskScore += failedAutoDebits * 5;
    riskScore += hasGambling ? 15 : 0;
    riskScore += hasLendingApps ? 10 : 0;
    riskScore += (expenses / income) > 0.7 ? 10 : 3;
    riskScore = Math.min(100, Math.max(0, riskScore + rand(-5, 5)));

    // Risk segment
    let riskSegment;
    if (riskScore >= 75) riskSegment = 'CRITICAL';
    else if (riskScore >= 50) riskSegment = 'HIGH RISK';
    else if (riskScore >= 30) riskSegment = 'MEDIUM RISK';
    else riskSegment = 'SAFE';

    // Investments (~80% have some, ~20% have none)
    const investmentCount = Math.random() < 0.2 ? 0 : rand(1, 4);
    const investments = [];
    const usedTypes = new Set();
    for (let i = 0; i < investmentCount; i++) {
        let type;
        do { type = pick(INVESTMENT_TYPES); } while (usedTypes.has(type));
        usedTypes.add(type);
        investments.push({ type, amount: rand(10000, 500000) });
    }

    const cardLast4Debit = String(rand(1000, 9999));
    const cardLast4Credit = hasCreditCard ? String(rand(1000, 9999)) : null;

    // Monthly balance history (6 months)
    const balanceHistory = [];
    let bal = debitBalance + rand(-50000, 100000);
    for (let m = 5; m >= 0; m--) {
        const date = new Date();
        date.setMonth(date.getMonth() - m);
        bal = Math.max(1000, bal + rand(-30000, 40000));
        balanceHistory.push({ month: date.toISOString().slice(0, 7), balance: bal });
    }

    // Monthly income vs expenses (3 months)
    const moneyFlow = [];
    for (let m = 2; m >= 0; m--) {
        const date = new Date();
        date.setMonth(date.getMonth() - m);
        moneyFlow.push({
            month: date.toISOString().slice(0, 7),
            income: income + rand(-5000, 5000),
            expenses: expenses + rand(-3000, 3000)
        });
    }

    // Credit utilization history (6 months)
    const creditHistory = [];
    if (hasCreditCard) {
        for (let m = 5; m >= 0; m--) {
            const date = new Date();
            date.setMonth(date.getMonth() - m);
            creditHistory.push({
                month: date.toISOString().slice(0, 7),
                utilization: round2(Math.min(100, Math.max(5, creditUtilPct + rand(-20, 20))))
            });
        }
    }

    // Expense breakdown categories
    const expenseBreakdown = {
        Shopping: rand(2000, 15000),
        'Food & Dining': rand(3000, 12000),
        Utilities: rand(1000, 5000),
        Transport: rand(500, 4000),
        Entertainment: rand(500, 8000),
        Groceries: rand(2000, 10000),
        Lifestyle: rand(500, 5000)
    };
    if (hasGambling) {
        expenseBreakdown['Gambling'] = rand(2000, 20000);
    }

    // EMI payment delay history (6 months)
    const emiDelays = [];
    for (let m = 5; m >= 0; m--) {
        const date = new Date();
        date.setMonth(date.getMonth() - m);
        emiDelays.push({
            month: date.toISOString().slice(0, 7),
            daysDelayed: latePayments > 0 ? rand(0, 30) : 0
        });
    }

    return {
        id: 1000 + id,
        name,
        age,
        gender,
        city,
        income,
        expenses,
        emiAmount,
        loanType,
        loanAmount,
        creditLimit,
        creditUsed,
        debitBalance,
        accountAge,
        riskScore,
        riskSegment,
        emiIncomeRatio,
        creditUtilPct,
        latePayments,
        failedAutoDebits,
        hasGambling: hasGambling ? 1 : 0,
        hasLendingApps: hasLendingApps ? 1 : 0,
        hasCreditCard: hasCreditCard ? 1 : 0,
        investments: JSON.stringify(investments),
        cardLast4Debit,
        cardLast4Credit,
        balanceHistory: JSON.stringify(balanceHistory),
        moneyFlow: JSON.stringify(moneyFlow),
        creditHistory: JSON.stringify(creditHistory),
        expenseBreakdown: JSON.stringify(expenseBreakdown),
        emiDelays: JSON.stringify(emiDelays)
    };
}

function generateTransactions(customerId, customer) {
    const txns = [];
    const numTxns = rand(30, 80);
    const now = new Date();

    for (let i = 0; i < numTxns; i++) {
        const daysAgo = rand(0, 365);
        const date = new Date(now);
        date.setDate(date.getDate() - daysAgo);
        date.setHours(rand(0, 23), rand(0, 59), 0, 0);

        const isCredit = Math.random() < 0.25;
        let merchant, category, isGambling = 0, isLendingApp = 0, isBounced = 0;

        if (!isCredit && customer.hasGambling && Math.random() < 0.15) {
            merchant = pick(GAMBLING_MERCHANTS);
            category = 'Gambling';
            isGambling = 1;
        } else if (!isCredit && customer.hasLendingApps && Math.random() < 0.1) {
            merchant = pick(LENDING_APPS);
            category = 'Lending App';
            isLendingApp = 1;
        } else {
            merchant = pick(MERCHANTS);
            category = pick(CATEGORIES);
        }

        // Some EMI auto-debits
        if (!isCredit && Math.random() < 0.05) {
            merchant = 'Bajaj Finance';
            category = 'EMI Auto-Debit';
            if (customer.failedAutoDebits > 0 && Math.random() < 0.3) {
                isBounced = 1;
            }
        }

        const amount = isCredit ? rand(5000, 100000) : rand(100, 25000);
        const mode = customer.hasCreditCard && Math.random() < 0.3 ? 'CC' : pick(['UPI', 'DC', 'NEFT', 'IMPS']);

        txns.push({
            customerId,
            date: date.toISOString(),
            merchant,
            category,
            mode,
            amount: isCredit ? amount : -amount,
            isGambling,
            isLendingApp,
            isBounced
        });
    }

    return txns.sort((a, b) => new Date(b.date) - new Date(a.date));
}

function seed() {
    // Check if data already exists
    const tableExists = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'").get();
    if (tableExists) {
        const count = db.prepare('SELECT COUNT(*) as cnt FROM customers').get();
        if (count.cnt > 0 && !process.argv.includes('--force')) {
            console.log(`Database already has ${count.cnt} customers. Use --force to re-seed.`);
            return;
        }
    }

    console.log('Seeding database with 1000 customers...');

    // Create tables
    db.exec(`
    DROP TABLE IF EXISTS transactions;
    DROP TABLE IF EXISTS interventions;
    DROP TABLE IF EXISTS customers;
    
    CREATE TABLE customers (
      id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      age INTEGER,
      gender TEXT,
      city TEXT,
      income INTEGER,
      expenses INTEGER,
      emi_amount INTEGER,
      loan_type TEXT,
      loan_amount INTEGER,
      credit_limit INTEGER DEFAULT 0,
      credit_used INTEGER DEFAULT 0,
      debit_balance INTEGER,
      account_age INTEGER,
      risk_score REAL,
      risk_segment TEXT,
      emi_income_ratio REAL,
      credit_util_pct REAL,
      late_payments INTEGER DEFAULT 0,
      failed_auto_debits INTEGER DEFAULT 0,
      has_gambling INTEGER DEFAULT 0,
      has_lending_apps INTEGER DEFAULT 0,
      has_credit_card INTEGER DEFAULT 0,
      investments TEXT DEFAULT '[]',
      card_last4_debit TEXT,
      card_last4_credit TEXT,
      balance_history TEXT DEFAULT '[]',
      money_flow TEXT DEFAULT '[]',
      credit_history TEXT DEFAULT '[]',
      expense_breakdown TEXT DEFAULT '{}',
      emi_delays TEXT DEFAULT '[]'
    );
    
    CREATE TABLE transactions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_id INTEGER NOT NULL,
      date TEXT NOT NULL,
      merchant TEXT,
      category TEXT,
      mode TEXT,
      amount REAL,
      is_gambling INTEGER DEFAULT 0,
      is_lending_app INTEGER DEFAULT 0,
      is_bounced INTEGER DEFAULT 0,
      FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    
    CREATE TABLE interventions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_id INTEGER NOT NULL,
      date TEXT NOT NULL,
      action TEXT NOT NULL,
      status TEXT DEFAULT 'Sent',
      analyst_name TEXT DEFAULT 'System',
      FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    
    CREATE INDEX idx_txn_customer ON transactions(customer_id);
    CREATE INDEX idx_txn_date ON transactions(date);
    CREATE INDEX idx_int_customer ON interventions(customer_id);
    CREATE INDEX idx_cust_risk ON customers(risk_segment);
    CREATE INDEX idx_cust_cc ON customers(has_credit_card);
  `);

    const insertCustomer = db.prepare(`
    INSERT INTO customers (id, name, age, gender, city, income, expenses, emi_amount, loan_type, loan_amount,
      credit_limit, credit_used, debit_balance, account_age, risk_score, risk_segment, emi_income_ratio,
      credit_util_pct, late_payments, failed_auto_debits, has_gambling, has_lending_apps, has_credit_card,
      investments, card_last4_debit, card_last4_credit, balance_history, money_flow, credit_history,
      expense_breakdown, emi_delays)
    VALUES (@id, @name, @age, @gender, @city, @income, @expenses, @emiAmount, @loanType, @loanAmount,
      @creditLimit, @creditUsed, @debitBalance, @accountAge, @riskScore, @riskSegment, @emiIncomeRatio,
      @creditUtilPct, @latePayments, @failedAutoDebits, @hasGambling, @hasLendingApps, @hasCreditCard,
      @investments, @cardLast4Debit, @cardLast4Credit, @balanceHistory, @moneyFlow, @creditHistory,
      @expenseBreakdown, @emiDelays)
  `);

    const insertTxn = db.prepare(`
    INSERT INTO transactions (customer_id, date, merchant, category, mode, amount, is_gambling, is_lending_app, is_bounced)
    VALUES (@customerId, @date, @merchant, @category, @mode, @amount, @isGambling, @isLendingApp, @isBounced)
  `);

    const insertAll = db.transaction(() => {
        for (let i = 1; i <= 1000; i++) {
            const customer = generateCustomer(i);
            insertCustomer.run(customer);

            const txns = generateTransactions(customer.id, customer);
            for (const txn of txns) {
                insertTxn.run(txn);
            }
        }
    });

    insertAll();

    // Print stats
    const total = db.prepare('SELECT COUNT(*) as cnt FROM customers').get().cnt;
    const ccCount = db.prepare('SELECT COUNT(*) as cnt FROM customers WHERE has_credit_card = 1').get().cnt;
    const critical = db.prepare("SELECT COUNT(*) as cnt FROM customers WHERE risk_segment IN ('CRITICAL', 'HIGH RISK')").get().cnt;
    const txnCount = db.prepare('SELECT COUNT(*) as cnt FROM transactions').get().cnt;

    console.log(`✓ Seeded ${total} customers (${ccCount} with credit cards, ${critical} high-risk/critical)`);
    console.log(`✓ Generated ${txnCount} transactions`);
}

seed();
