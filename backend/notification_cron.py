"""Scheduled runner: starts independently of the web API and exits after dispatch."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / '.env')


async def main():
    from services.notification_outbox import NotificationOutbox
    from services.whatsapp_reminder_dispatcher import WhatsAppReminderDispatcher
    client = AsyncIOMotorClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=10000)
    try:
        db = client[os.environ.get('DB_NAME', 'foundations_db')]
        await NotificationOutbox.indexes(db)
        await WhatsAppReminderDispatcher.dispatch_due(db)
    finally:
        client.close()


if __name__ == '__main__':
    asyncio.run(main())
