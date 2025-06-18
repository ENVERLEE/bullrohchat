import oracledb

# Oracle Instant Client 23ai가 설치된 경로로 수정하세요!
oracledb.init_oracle_client(lib_dir=r"C:\instantclient_23_8")

print(oracledb.clientversion())
