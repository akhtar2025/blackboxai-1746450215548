from flask import Flask, render_template, request, jsonify, send_file, g
import sqlite3
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)

DATABASE = 'work_planner.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('database/schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/records', methods=['GET'])
def get_records():
    name_filter = request.args.get('name', '').strip()
    db = get_db()
    cur = db.cursor()
    if name_filter:
        query = 'SELECT * FROM work_records WHERE name LIKE ? ORDER BY created_at DESC'
        cur.execute(query, ('%' + name_filter + '%',))
    else:
        query = 'SELECT * FROM work_records ORDER BY created_at DESC'
        cur.execute(query)
    records = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()]
    return jsonify(records)

@app.route('/api/records', methods=['POST'])
def add_record():
    data = request.json
    db = get_db()
    cur = db.cursor()
    
    try:
        cur.execute(
            'INSERT INTO work_records (npk, name, work_results, work_plan) VALUES (?, ?, ?, ?)',
            (data['npk'], data['name'], data['work_results'], data['work_plan'])
        )
        db.commit()
        return jsonify({"success": True, "id": cur.lastrowid}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/export', methods=['GET'])
def export_excel():
    db = get_db()
    query = 'SELECT npk, name, work_results, work_plan, created_at FROM work_records ORDER BY created_at DESC'
    df = pd.read_sql_query(query, db)
    
    # Format the date
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Create Excel file
    filename = f'work_records_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    excel_path = os.path.join('static', 'exports', filename)
    os.makedirs(os.path.dirname(excel_path), exist_ok=True)
    
    df.to_excel(excel_path, index=False, sheet_name='Work Records')
    return send_file(excel_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
