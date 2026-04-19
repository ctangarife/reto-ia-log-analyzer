"""Test script for exercises endpoint"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import db_manager
from services.course_service import course_service
from uuid import UUID

async def test_exercises():
    """Test the get_project_exercises function"""
    # Connect to databases
    await db_manager.connect_postgres()
    await db_manager.connect_mongodb()

    project_id = UUID('fcc9008c-3a09-4244-ba44-30c23fdc4861')
    user_id = UUID('018ff1fe-5be3-7f0a-9e4b-cf98e9287520')  # Admin user

    print("=== TESTING EXERCISES ENDPOINT ===\n")

    # Get lesson IDs for the published course
    async with db_manager.postgres_pool.acquire() as conn:
        lessons = await conn.fetch('''
            SELECT l.id, l.title, l.exercise_data
            FROM learning.course_lessons l
            JOIN learning.course_modules m ON m.id = l.module_id
            JOIN learning.courses c ON c.id = m.course_id
            WHERE c.status = 'published'
            AND (l.title LIKE '%Práctico%' OR l.title LIKE '%Examen%')
            ORDER BY l.lesson_order
        ''')

        print(f"Found {len(lessons)} lessons with exercises\n")

        for lesson in lessons:
            print(f'Lesson: {lesson["title"]}')
            print(f'  ID: {lesson["id"]}')
            print(f'  exercise_data: {lesson["exercise_data"]}')

            # Test get_project_exercises
            try:
                exercises = await course_service.get_project_exercises(user_id, project_id, lesson['id'], 3)
                print(f'  Exercises returned: {len(exercises)}')
                if exercises:
                    print(f'  First exercise: {exercises[0]}')
                else:
                    print('  No exercises returned!')
            except Exception as e:
                print(f'  ERROR: {e}')
                import traceback
                traceback.print_exc()
            print()

if __name__ == "__main__":
    asyncio.run(test_exercises())
