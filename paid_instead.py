import streamlit as st
import psycopg2
import datetime
import pandas as pd
from dateutil.relativedelta import relativedelta
import os

def main():
    st.write(os.environ["USERNAME"])
    persons = [st.secrets["person1"],st.secrets["person2"]]

    st.subheader("生活費計算")

    tab_input,tab_result,tab_edit = st.tabs(["入力", "月次結果", "データ編集"])

    categories = get_categories()

    # データ登録タブ
    with tab_input:
        col_date,col_item,col_cat = st.columns(3)
        with col_date:
            date = st.date_input("日付")
        with col_item:
            bought_item = st.text_input("買ったもの")
        with col_cat:
            category = st.selectbox("カテゴリー",categories)

        col_price,col_person = st.columns(2)
        with col_price:
            price = st.text_input("価格")
        with col_person:
            paid_person = st.radio("払った人",persons,horizontal=True)

        if st.button("登録"):
            if not price:
                st.warning("価格を入力してください。")
            elif not bought_item:
                st.warning("買ったものを入力してください。")
            else:
                try:
                    add_pay_history(date,bought_item,price,paid_person,category)
                except Exception as e:
                    st.error(f"データ登録に失敗しました。\n{e}")
                else:
                    st.experimental_rerun()
                st.success("データ登録に成功しました。")

    # 支払い履歴を取得
    pay_history_df = get_pay_history()

    # 月次集計結果タブ
    with tab_result:
        past_month_limit = 1  # 何か月前まで表示するか
        for i in range(past_month_limit+1):
            display_month = (datetime.datetime.now() - relativedelta(months=i)).strftime("%Y%m")

            st.subheader(f"＜{int(display_month[-2:])}月＞")

            monthly_pay_history_df = pay_history_df[pd.to_datetime(pay_history_df["日付"]).dt.strftime("%Y%m")==display_month]
            monthly_result_by_person = monthly_pay_history_df.groupby("人").sum()

            # 各自の支払額をリスト化
            total_payments = []
            for person in persons:
                try:
                    total_payments.append(monthly_result_by_person.at[person,"値段"])
                except KeyError:
                    total_payments.append(0)

            # 各自の合計金額を表示
            st.subheader(f"{persons[0]}:{total_payments[0]}円 {persons[1]}:{total_payments[1]}円")
            # 差額算出
            difference = abs(total_payments[0]-total_payments[1])

            # 集計結果表示
            if total_payments[0] > total_payments[1]:
                st.subheader(f" {persons[1]}が{difference}円支払う","result")
            elif total_payments[0] < total_payments[1]:
                st.subheader(f" {persons[0]}が{difference}円支払う","result")
            else:
                st.subheader(" 支払額は同じ")

    # 履歴確認&削除タブ
    with tab_edit:
        pay_history_df = pay_history_df.sort_values("日付")
        col_delete,col_display = st.columns(2)

        with col_delete:
            try:
                id = st.number_input("削除するidを入力",pay_history_df["id"].min(),pay_history_df["id"].max(),value = pay_history_df["id"].max())
                st.subheader(f"{pay_history_df[pay_history_df['id']==id].iat[0,2]}")
                if st.button("削除"):
                    delete_pay_history(id)
                    st.experimental_rerun()
            except:
                pass

        with col_display:
            pay_history_df = pay_history_df.set_index("id")
            st.dataframe(pay_history_df.iloc[::-1],height=250)


def conn_supabase():
    ip = st.secrets["host"]
    port = st.secrets["port"]
    dbname = st.secrets["dbname"]
    user = st.secrets["user"]
    pw = st.secrets["password"]

    return f"host={ip} port={port} dbname={dbname} user={user} password={pw}"

# カテゴリーを取得
def get_categories():
    sql = f"""
        SELECT category
        FROM household_expenses.ms_category
        """

    with psycopg2.connect(conn_supabase()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            data = cur.fetchall()

    categories = [update_category[0] for update_category in data]

    return categories

# 支払い履歴追加
def add_pay_history(date,bought_item,price,paid_person,category):
    sql = f"""
        INSERT INTO household_expenses.tr_paid_instead
            (date,bought_items,price,person,category_id)
        VALUES (
            \'{date}\',
            \'{bought_item}\',
            {price},
            \'{paid_person}\',
            (SELECT category_id
             FROM household_expenses.ms_category
             WHERE category = \'{category}\')
        )
        """
    with psycopg2.connect(conn_supabase()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()

# 支払い履歴取得
def get_pay_history():
    sql = f"""
        SELECT
            paid_instead_id,
            date,
            bought_items,
            price,
            person
        FROM household_expenses.tr_paid_instead
    """
    with psycopg2.connect(conn_supabase()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            data = cur.fetchall()

    colnames =["id","日付","買い物","値段","人"]
    pay_history_df = pd.DataFrame(data,columns=colnames)

    return pay_history_df

# 支払い履歴削除
def delete_pay_history(id):
    sql = f"""
        DELETE FROM household_expenses.tr_paid_instead
        WHERE paid_instead_id = {id}
        """
    with psycopg2.connect(conn_supabase()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()

main()