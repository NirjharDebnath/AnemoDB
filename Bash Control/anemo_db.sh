sudo systemctl start postgresql
cd ..
cd Cache\ Components/
g++ -std=c++17 main.cpp -o anemo_db -lpqxx -lpq -pthread
./anemo_db
