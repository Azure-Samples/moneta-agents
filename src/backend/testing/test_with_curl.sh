curl -X POST "http://localhost:8000/http_trigger" \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": "sk_test_ins_3",  
           "chat_id": null,  
           "message": "Hello",  
           "load_history": true,  
           "use_case": "fsi_banking"  
         }'  