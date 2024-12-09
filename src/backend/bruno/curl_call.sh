curl -X POST "http://localhost/http_trigger" \  
     -H "Content-Type: application/json" \  
     -d '{  
           "user_id": "user123",  
           "chat_id": null,  
           "message": "Hello",  
           "load_history": false,  
           "use_case": "fsi_banking"  
         }'  