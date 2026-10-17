
import sqlite3
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st


# Page settings
st.set_page_config(
    page_title="Student Expense Tracker",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Student Expense Tracker")
st.write("Track your expenses and manage your budget.")


# Database setup
conn = sqlite3.connect("expenses.db")

conn.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_date TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT
    )
""")
conn.commit()


# Add expense form
st.subheader("Add a New Expense")

with st.form("expense_form"):
    expense_date = st.date_input("Date", value=date.today())

    category = st.selectbox(
        "Category",
        ["Food", "Transport", "Education",
         "Shopping", "Bills", "Other"]
    )

    amount = st.number_input(
        "Amount (₹)",
        min_value=0.01,
        step=10.0
    )

    description = st.text_input("Description")

    submitted = st.form_submit_button("Add Expense")

    if submitted:
        conn.execute(
            """
            INSERT INTO expenses
            (expense_date, category, amount, description)
            VALUES (?, ?, ?, ?)
            """,
            (
                expense_date.isoformat(),
                category,
                amount,
                description
            )
        )
        conn.commit()
        st.success("Expense added successfully!")
        st.rerun()


# Load transactions
df = pd.read_sql_query(
    "SELECT * FROM expenses ORDER BY expense_date DESC, id DESC",
    conn
)

st.divider()
st.subheader("Expense Dashboard")


if df.empty:
    st.info("No expenses yet. Add your first expense above!")

else:
    df["expense_date"] = pd.to_datetime(df["expense_date"])
    df["month"] = df["expense_date"].dt.strftime("%Y-%m")

    # Monthly filter
    months = sorted(df["month"].unique(), reverse=True)

    selected_month = st.selectbox("Select Month", months)

    monthly_df = df[df["month"] == selected_month].copy()

    # Budget
    st.subheader("Monthly Budget")

    budget = st.number_input(
        "Set your budget (₹)",
        min_value=100.0,
        value=5000.0,
        step=500.0,
        key="monthly_budget"
    )

    total_expenses = monthly_df["amount"].sum()
    remaining = budget - total_expenses

    col1, col2, col3 = st.columns(3)

    col1.metric("Monthly Expenses", f"₹{total_expenses:,.2f}")
    col2.metric("Monthly Budget", f"₹{budget:,.2f}")
    col3.metric("Budget Remaining", f"₹{remaining:,.2f}")

    st.progress(min(total_expenses / budget, 1.0))

    if remaining < 0:
        st.warning("You have exceeded your monthly budget!")
    else:
        st.success("You are within your monthly budget.")

    # Overall summary
    st.subheader("Overall Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric("All-Time Expenses", f"₹{df['amount'].sum():,.2f}")
    col2.metric("Total Transactions", len(df))
    col3.metric("Average Expense", f"₹{df['amount'].mean():,.2f}")

    # Spending by category
    st.subheader("Spending by Category")

    category_totals = (
        monthly_df.groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
    )

    fig = px.pie(
        category_totals,
        names="category",
        values="amount",
        hole=0.4,
        title=f"Expense Distribution — {selected_month}"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Monthly spending trend
    st.subheader("Monthly Spending Trend")

    monthly_trend = (
        df.groupby("month", as_index=False)["amount"]
        .sum()
        .sort_values("month")
    )

    fig_trend = px.bar(
        monthly_trend,
        x="month",
        y="amount",
        title="Expenses by Month",
        labels={
            "month": "Month",
            "amount": "Total Expenses (₹)"
        }
    )

    st.plotly_chart(fig_trend, use_container_width=True)

    # Transactions
    st.subheader("Monthly Transactions")

    display_df = monthly_df[
        ["id", "expense_date", "category", "amount", "description"]
    ].copy()

    display_df["expense_date"] = (
        display_df["expense_date"].dt.strftime("%Y-%m-%d")
    )

    st.dataframe(display_df, use_container_width=True)

    # CSV export
    csv_data = monthly_df[
        ["expense_date", "category", "amount", "description"]
    ].copy()

    csv_data["expense_date"] = (
        csv_data["expense_date"].dt.strftime("%Y-%m-%d")
    )

    st.download_button(
        label="Download Monthly Expenses as CSV",
        data=csv_data.to_csv(index=False).encode("utf-8"),
        file_name=f"expenses_{selected_month}.csv",
        mime="text/csv"
    )
    
    st.subheader("Edit an Expense")

    edit_options = {
        f"ID {row.id} | {row.expense_date.strftime('%Y-%m-%d')} | {row.category} | ₹{row.amount:.2f}": int(row.id)
        for row in monthly_df.itertuples()
    }

    selected_edit = st.selectbox(
        "Select expense to edit",
        list(edit_options.keys()),
        key="edit_expense"
    )

    selected_id = edit_options[selected_edit]

    expense_to_edit = monthly_df[monthly_df["id"] == selected_id].iloc[0]

    with st.form("edit_expense_form"):
        new_date = st.date_input(
            "Edit date",
            value=expense_to_edit["expense_date"].date()
        )

        categories = ["Food", "Transport", "Education", "Shopping", "Bills", "Other"]
        new_category = st.selectbox(
            "Edit category",
            categories,
            index=categories.index(expense_to_edit["category"])
        )

        new_amount = st.number_input(
            "Edit amount (₹)",
            min_value=0.01,
            value=float(expense_to_edit["amount"]),
            step=10.0
        )

        new_description = st.text_input(
            "Edit description",
            value=str(expense_to_edit["description"] or "")
        )

        update_button = st.form_submit_button("Update Expense")

        if update_button:
            conn.execute(
                """UPDATE expenses
                   SET expense_date = ?, category = ?, amount = ?, description = ?
                   WHERE id = ?""",
                (
                    new_date.isoformat(),
                    new_category,
                    new_amount,
                    new_description,
                    selected_id
                )
            )
            conn.commit()
            st.success("Expense updated successfully!")
            st.rerun()


    # Delete an expense
    st.subheader("Delete an Expense")

    transaction_options = {
        f"ID {row.id} | {row.expense_date.strftime('%Y-%m-%d')} | "
        f"{row.category} | ₹{row.amount:.2f} | {row.description}":
        int(row.id)
        for row in monthly_df.itertuples()
    }

    selected_transaction = st.selectbox(
        "Select transaction to delete",
        list(transaction_options.keys())
    )

    if st.button("Delete Selected Expense", type="secondary"):
        selected_id = transaction_options[selected_transaction]

        conn.execute(
            "DELETE FROM expenses WHERE id = ?",
            (selected_id,)
        )
        conn.commit()

        st.success("Expense deleted successfully!")
        st.rerun()


conn.close()
