# backend/seed_data.py

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import UUID

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.models.database import Base, Project, Section, ChecklistItem
from backend.app.models.database import SectionType, ChecklistStatus, Framework
from backend.app.config import settings

def seed_database():
    # Create engine and session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Create a mock user ID (in production, this would come from auth)
        user_id = UUID("12345678-1234-5678-1234-567812345678")

        # Create sample project
        project = Project(
            owner_id=user_id,
            title="The Last Journey",
            framework=Framework.THREE_ACT
        )
        db.add(project)
        db.commit()

        # Create sections
        sections_data = [
            {
                "type": SectionType.INCITING_INCIDENT,
                "user_notes": "Sarah discovers an ancient map in her grandmother's attic that leads to a forgotten civilization."
            },
            {
                "type": SectionType.PLOT_POINT_1,
                "user_notes": "Despite warnings from locals, Sarah decides to embark on the journey to find the lost city."
            },
            {
                "type": SectionType.MIDPOINT,
                "user_notes": "Sarah realizes the map is incomplete and she needs to find the missing pieces scattered across dangerous territories."
            },
            {
                "type": SectionType.PLOT_POINT_2,
                "user_notes": "Sarah's rival archaeologist steals the completed map, leaving her stranded in hostile territory."
            },
            {
                "type": SectionType.CLIMAX,
                "user_notes": "Sarah must navigate ancient traps and confront her rival in the heart of the lost city."
            },
            {
                "type": SectionType.RESOLUTION,
                "user_notes": "Sarah secures the artifacts for a museum, ensuring the preservation of history, and finds a new purpose in life."
            }
        ]

        for section_data in sections_data:
            section = Section(
                project_id=project.id,
                **section_data
            )
            db.add(section)
            db.commit()

            # Add checklist items for the first section
            if section.type == SectionType.INCITING_INCIDENT:
                checklist_items = [
                    {
                        "prompt": "What event disrupts the protagonist's normal life?",
                        "answer": "Finding the ancient map in her grandmother's attic",
                        "status": ChecklistStatus.COMPLETE,
                        "order": 0
                    },
                    {
                        "prompt": "How does this incident force the protagonist to act?",
                        "answer": "The map reveals a location that could change historical understanding",
                        "status": ChecklistStatus.COMPLETE,
                        "order": 1
                    },
                    {
                        "prompt": "What's at stake if the protagonist doesn't respond?",
                        "answer": "The location might be lost forever or fall into the wrong hands",
                        "status": ChecklistStatus.COMPLETE,
                        "order": 2
                    }
                ]

                for item_data in checklist_items:
                    item = ChecklistItem(
                        section_id=section.id,
                        **item_data
                    )
                    db.add(item)
                
                db.commit()

        print("✅ Database seeded successfully!")

    except Exception as e:
        print(f"❌ Error seeding database: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
