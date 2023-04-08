from aiosqlite import connect

class DB:
    def __init__(self) -> None:
        return
    
    async def load_db(self, path):
        self.conn = await connect(path)
        self.curr = await self.conn.cursor()
        
    async def request(self, req: str, args: tuple = None):
        res =  await self.curr.execute(req, args)
        await self.conn.commit()
        return res
    
    async def get_fetchone(self, req: str, args: tuple = None):
        res =  await self.curr.execute(req, args)
        await self.conn.commit()
        return await res.fetchone()
    
    async def get_fetchall(self, req: str, args: tuple = None):
        res =  await self.curr.execute(req, args)
        await self.conn.commit()
        return await res.fetchall()
    
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
