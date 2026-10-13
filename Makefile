CXX ?= g++
CXXFLAGS := -std=c++17 -O3 -Wall -Wextra -pthread
LDFLAGS := -lpqxx -lpq -pthread
PREFIX ?= /usr/local
BINDIR := $(PREFIX)/bin

SRC_DIR := Cache\ Components
SRCS := $(SRC_DIR)/main.cpp
HEADERS := $(SRC_DIR)/CacheEngine.hpp $(SRC_DIR)/Cache.hpp $(SRC_DIR)/ConnectionPool.hpp $(SRC_DIR)/ThreadSafeQueue.hpp
TARGET := anemo_db

all: $(TARGET)

$(TARGET): $(SRCS) $(HEADERS)
	@echo ">>> Compiling Anemo DB (-O3 Release)..."
	$(CXX) $(CXXFLAGS) $(SRCS) -o $(TARGET) $(LDFLAGS)
	@echo ">>> Build complete: ./$(TARGET)"

run: $(TARGET)
	@echo ">>> Launching Anemo DB..."
	./$(TARGET)

install: $(TARGET)
	@echo ">>> Installing Anemo DB to $(BINDIR)..."
	install -d $(DESTDIR)$(BINDIR)
	install -m 755 $(TARGET) $(DESTDIR)$(BINDIR)/$(TARGET)
	@echo ">>> Installation complete! You can now run 'anemo_db' from anywhere."

uninstall:
	@echo ">>> Uninstalling Anemo DB from $(BINDIR)..."
	rm -f $(DESTDIR)$(BINDIR)/$(TARGET)
	@echo ">>> Uninstalled successfully."

clean:
	@echo ">>> Cleaning build artifacts..."
	rm -f $(TARGET) $(SRC_DIR)/anemo_db

dashboard:
	@echo ">>> Launching AnemoDB Telemetry Web Dashboard (http://127.0.0.1:5000)..."
	python3 "Web Dashboard/web_dashboard.py"

monitor:
	@echo ">>> Launching AnemoDB Terminal Telemetry Monitor..."
	python3 "Cache Monitor/monitor_cache.py"

.PHONY: all run install uninstall clean dashboard monitor
