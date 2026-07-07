# test_redis.py
import redis

# Your correct password
PASSWORD = "gQAAAAAAAbqKAAIgcDI1ODMxZjIyYmVjMGU0YTA0YTU1OGNiZmRkZTJkYjAzZQ"

try:
    r = redis.Redis(
        host='electric-caiman-113290.upstash.io',
        port=6379,
        password=PASSWORD,
        ssl=True,
        ssl_cert_reqs=None,
        decode_responses=True,
        socket_timeout=10,
        socket_connect_timeout=10
    )
    
    r.ping()
    print("✅ Redis Connected Successfully!")
    
    # Test operations
    r.set("test", "ClinicConnect Works!")
    value = r.get("test")
    print(f"✅ Read: {value}")
    
    r.delete("test")
    print("✅ All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")