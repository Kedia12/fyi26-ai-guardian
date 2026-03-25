def print_banner():
    print("=== Guardian Module Running ===")


def format_alert(alert):
    return (
        f"[{alert['severity']}] "
        f"{alert['reason_code']} | "
        f"confidence={alert['confidence']:.2f} | "
        f"action={alert['recommended_action']} | "
        f"status={alert['alert_status']}"
    )


def print_replay_summary(total_rows, total_alerts):
    print("\nReplay complete.")
    print(f"Rows processed: {total_rows}")
    print(f"Alerts generated: {total_alerts}")
    