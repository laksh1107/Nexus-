from app.engine import analyse, demo_logs
def test_database_root_cause():
    result=analyse(demo_logs("database"),"test")
    assert result["total_logs"] > 0
    assert result["anomaly_count"] > 0
    assert result["incidents"][0]["cause_key"] == "database"
def test_memory_root_cause():
    result=analyse(demo_logs("memory"),"test")
    assert result["incidents"][0]["cause_key"] == "memory"
def test_config_root_cause():
    result=analyse(demo_logs("configuration"),"test")
    assert result["incidents"][0]["cause_key"] == "configuration"
