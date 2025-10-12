# To Run the project

# run env

Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\env\Scripts\Activate.ps1

# avec uvicorn directement pour backend

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# frontend

cd frontend
npm start
