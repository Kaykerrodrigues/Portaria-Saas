import sqlite3
conn = sqlite3.connect('portaria.db')
conn.execute("DELETE FROM condominios")
conn.execute("DELETE FROM usuarios WHERE perfil != 'superadmin'")
conn.commit()
conn.close()
print("Banco limpo com sucesso!")
