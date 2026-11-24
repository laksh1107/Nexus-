"""Evaluate binary anomaly labels against detector output for a prepared CSV.
Required columns: message,label (label values 0/1 or normal/anomaly).
"""
import argparse, pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
from app.engine import analyse
def main():
    p=argparse.ArgumentParser();p.add_argument("csv");p.add_argument("--message-col",default="message");p.add_argument("--label-col",default="label");a=p.parse_args()
    df=pd.read_csv(a.csv).dropna(subset=[a.message_col,a.label_col])
    text="\n".join(df[a.message_col].astype(str))
    result=analyse(text,"evaluation")
    y_true=df[a.label_col].astype(str).str.lower().isin(["1","true","anomaly","abnormal","yes"]).astype(int)
    y_pred=pd.Series([int(x["is_anomaly"]) for x in result["logs"][:len(y_true)]])
    print("Rows:",len(y_true));print(confusion_matrix(y_true,y_pred));print(classification_report(y_true,y_pred,zero_division=0))
if __name__=="__main__":main()
