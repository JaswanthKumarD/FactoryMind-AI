try:
    from .database import init_db, get_conn
except ImportError:
    from database import init_db, get_conn

def seed():
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    for t in ["machines","orders","inventory","routes"]:
        cur.execute(f"DELETE FROM {t}")

    machines = [
        ("CNC-01","CNC Turning 01","Turning",100,500,16,"Available"),
        ("CNC-02","CNC Turning 02","Turning",80,450,16,"Available"),
        ("CNC-03","CNC Milling 01","Milling",70,600,16,"Available"),
        ("CNC-04","CNC Drilling 01","Drilling",120,350,16,"Available"),
        ("GR-01","Precision Grinder","Grinding",90,550,16,"Available"),
        ("HT-01","Heat Treatment","Heat Treatment",150,700,16,"Available")
    ]
    cur.executemany("""INSERT INTO machines
        (code,name,machine_type,capacity_per_hour,cost_per_hour,available_hours,status)
        VALUES(?,?,?,?,?,?,?)""", machines)

    orders = [
        ("O101","Shaft",500,1,24,"Steel","Pending"),
        ("O102","Gear",300,2,36,"Alloy","Pending"),
        ("O103","Bracket",400,1,28,"Steel","Pending"),
        ("O104","Coupling",250,3,48,"Steel","Pending"),
        ("O105","Gear",200,2,42,"Alloy","Pending"),
        ("O106","Shaft",350,2,40,"Steel","Pending")
    ]
    cur.executemany("""INSERT INTO orders
        (order_code,product,quantity,priority,deadline_hours,material,status)
        VALUES(?,?,?,?,?,?,?)""", orders)

    inventory = [
        ("Steel",3500,"kg"), ("Alloy",2200,"kg"), ("Lubricant",600,"L")
    ]
    cur.executemany("INSERT INTO inventory(material,quantity,unit) VALUES(?,?,?)", inventory)

    routes = [
        ("Shaft","Turning",1,0.010),("Shaft","Drilling",2,0.004),
        ("Shaft","Heat Treatment",3,0.003),("Shaft","Grinding",4,0.008),
        ("Gear","Turning",1,0.012),("Gear","Milling",2,0.014),
        ("Gear","Heat Treatment",3,0.004),("Gear","Grinding",4,0.010),
        ("Bracket","Milling",1,0.012),("Bracket","Drilling",2,0.005),
        ("Bracket","Grinding",3,0.006),
        ("Coupling","Turning",1,0.011),("Coupling","Milling",2,0.010),
        ("Coupling","Grinding",3,0.007)
    ]
    cur.executemany("""INSERT INTO routes
        (product,machine_type,sequence,hours_per_unit) VALUES(?,?,?,?)""", routes)
    conn.commit()
    conn.close()
    print("FactoryMind sample data loaded.")

if __name__ == "__main__":
    seed()
