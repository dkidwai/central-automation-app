import sqlite3
import pandas as pd

DB_PATH = 'app.db'

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def save_sheet_to_db(sheet_name, df):
    conn = get_conn()
    # Remove Unnamed columns (robust)
    df = df.loc[:, [col for col in df.columns if not str(col).lower().startswith("unnamed")]]
    df.to_sql(sheet_name, conn, if_exists='replace', index=False)
    conn.close()


def load_sheet_from_db(sheet_name):
    conn = get_conn()
    try:
        df = pd.read_sql(f'SELECT * FROM "{sheet_name}"', conn)
        df = df.astype(str)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def delete_row(sheet_name, row_id, id_col):
    conn = get_conn()
    conn.execute(f'DELETE FROM "{sheet_name}" WHERE "{id_col}"=?', (row_id,))
    conn.commit()
    conn.close()

def add_row(sheet_name, row_dict):
    conn = get_conn()
    columns = ','.join([f'"{c}"' for c in row_dict])
    placeholders = ','.join(['?']*len(row_dict))
    values = list(row_dict.values())
    conn.execute(f'INSERT INTO "{sheet_name}" ({columns}) VALUES ({placeholders})', values)
    conn.commit()
    conn.close()


def save_sheet_to_db(sheet_name, df):
    conn = get_conn()
    # Remove all unnamed columns
    df = df.loc[:, [col for col in df.columns if not str(col).lower().startswith("unnamed")]]
    # Skip saving if DataFrame is empty or has no columns
    if df.empty or len(df.columns) == 0:
        conn.close()
        return
    df.to_sql(sheet_name, conn, if_exists='replace', index=False)
    conn.close()


def update_row(sheet_name, row_id, id_col, row_dict):
    conn = get_conn()
    set_clause = ','.join([f'"{c}"=?' for c in row_dict])
    values = list(row_dict.values()) + [row_id]
    conn.execute(f'UPDATE "{sheet_name}" SET {set_clause} WHERE "{id_col}"=?', values)
    conn.commit()
    conn.close()
