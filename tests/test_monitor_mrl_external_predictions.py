

def test_evaluation_env_includes_compatible_pypath():
    from monitor_mrl_external_predictions import evaluation_env
    assert evaluation_env()["PYTHONPATH"].split(":")[0] == "/root/rna-ft-eval/pypath"
