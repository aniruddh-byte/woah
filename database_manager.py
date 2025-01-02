import sqlite3
import os
import pandas as pd
import streamlit as st
import json

class DatabaseManager:
    def __init__(self, db_path='project_management.db'):
        self._db_path = db_path
        self._ensure_tables_exist()

    def _get_connection(self):
        """
        Create a new connection for each database operation.
        This helps avoid threading issues.
        """
        return sqlite3.connect(self._db_path)

    def _ensure_tables_exist(self):
        """
        Ensure all necessary tables are created
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                project TEXT PRIMARY KEY,
                description TEXT,
                created_by TEXT,
                team_lead TEXT,
                date TEXT
            )
        ''')

        # Project paths table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_paths (
                file_name TEXT PRIMARY KEY,
                file_path TEXT
            )
        ''')

        # File details table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_details (
                project TEXT,
                fileID TEXT,
                title TEXT,
                summary TEXT,
                category TEXT,
                date TEXT,
                version TEXT,
                PRIMARY KEY (project, fileID)
            )
        ''')

        # Categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                categories TEXT NOT NULL
            )
        ''')

        # Questionnaires table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questionnaires (
                name TEXT PRIMARY KEY,
                category TEXT,
                user TEXT,
                description TEXT,
                date TEXT
            )
        ''')

        # Questions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questionnaire_questions (
                q_id INTEGER PRIMARY KEY AUTOINCREMENT,
                questionnaire_name TEXT,
                identifier TEXT,
                question TEXT
            )
        ''')
        
        # Reports Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    questionnaire TEXT NOT NULL,
                    name TEXT NOT NULL,
                    num_docs INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )           
        ''')
        
        #report_documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS report_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                content TEXT,
                FOREIGN KEY (report_id) REFERENCES reports(id)
            )                       
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questionnaire_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                question_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                answer TEXT,
                reference TEXT,
                FOREIGN KEY (report_id) REFERENCES reports(id)
            )               
        ''')
        
        conn.commit()
        conn.close()

    # Existing project-related methods...
    def get_all_projects(self):
        """
        Fetch all projects with a new connection
        Ensure proper column names and data formatting
        """
        conn = self._get_connection()
        try:
            query = """
                SELECT 
                    project, 
                    description, 
                    created_by, 
                    team_lead, 
                    date 
                FROM projects
            """
            df = pd.read_sql_query(query, conn)
            
            # Debug print to check retrieved data
            print("Retrieved Projects:")
            print(df)
            
            # Ensure column names match the expected format
            df.columns = ['project', 'description', 'created_by', 'team_lead', 'date']
            
            return df
        except Exception as e:
            st.error(f"Error retrieving projects: {e}")
            return pd.DataFrame(columns=['project', 'description', 'created_by', 'team_lead', 'date'])
        finally:
            conn.close()

    def insert_project(self, project, description, created_by, team_lead, date):
        """
        Insert a new project with a new connection
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO projects 
                (project, description, created_by, team_lead, date) 
                VALUES (?, ?, ?, ?, ?)
            ''', (project, description, created_by, team_lead, date))
            conn.commit()
            st.success(f"Project '{project}' created successfully!")
        except sqlite3.Error as e:
            st.error(f"Error creating project: {e}")
        finally:
            conn.close()

    def get_project_details(self, project_name):
        """Fetch detailed information about a specific project."""
        query = """
        SELECT 
            project, 
            description, 
            created_by, 
            team_lead, 
            date 
        FROM projects
        WHERE project = ?
        """
        df = pd.read_sql_query(query, self._get_connection(), params=(project_name,))
        return df.iloc[0] if not df.empty else None
    
    def insert_project_path(self, project, path):
        """
        Insert project path with a new connection
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO project_paths 
                (file_name, file_path) 
                VALUES (?, ?)
            ''', (project, path))
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Error storing project path: {e}")
        finally:
            conn.close()

    def delete_project(self, project_name):
        """
        Delete a project with a new connection
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Delete project from projects table
            cursor.execute("DELETE FROM projects WHERE project = ?", (project_name,))
            
            # Delete project path
            cursor.execute("DELETE FROM project_paths WHERE file_name = ?", (project_name,))
            
            # Delete associated file details
            cursor.execute("DELETE FROM file_details WHERE project = ?", (project_name,))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            st.error(f"Error deleting project: {e}")
            return False
        finally:
            conn.close()

    def get_all_questionnaires(self):
        """Get all questionnaires from database."""
        try:
            query = """
                SELECT name, category,
                       user, description, date
                FROM questionnaires
            """
            return pd.read_sql_query(query, self._get_connection())
        except Exception as e:
            print(f"Error getting questionnaires: {e}")
            return pd.DataFrame()

    def insert_questionnaire(self, name, category, user, description, date_str):
        """
        Insert a new questionnaire with a new connection
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO questionnaires 
                (name, category, user, description, date) 
                VALUES (?, ?, ?, ?, ?)
            ''', (name, category, user, description, date_str))
            conn.commit()
            st.success(f"Questionnaire '{name}' created successfully!")
            return True
        except sqlite3.Error as e:
            st.error(f"Error creating questionnaire: {e}")
            return False
        finally:
            conn.close()
            
    def save_questions_from_csv(self, questionnaire_name, questions_df):
        """
        Save questions from a CSV file to the database.
        Takes first column as identifier and second column as question.

        Args:
            questionnaire_name (str): Name of the questionnaire
            questions_df (pd.DataFrame): DataFrame containing questions data
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Delete existing questions for this questionnaire
            cursor.execute("DELETE FROM questionnaire_questions WHERE questionnaire_name = ?", 
                         (questionnaire_name,))

            # Use first column as identifier and second column as question
            identifier_col = questions_df.columns[0]
            question_col = questions_df.columns[1]

            # Insert new questions
            for _, row in questions_df.iterrows():
                cursor.execute('''
                    INSERT INTO questionnaire_questions 
                    (questionnaire_name, identifier, question)
                    VALUES (?, ?, ?)
                ''', (questionnaire_name, str(row[identifier_col]), row[question_col]))

            conn.commit()
            return True
        except sqlite3.Error as e:
            st.error(f"Error saving questions: {e}")
            return False
        finally:
            conn.close()

    def get_questionnaire_questions(self, questionnaire_name):
        """
        Get questions for a specific questionnaire with their numbers.
        """
        conn = self._get_connection()
        try:
            query = """
                SELECT identifier as number, question as Question
                FROM questionnaire_questions
                WHERE questionnaire_name = ?
                ORDER BY CAST(identifier AS INTEGER)
            """
            df = pd.read_sql_query(query, conn, params=(questionnaire_name,))
            return df
        except Exception as e:
            st.error(f"Error retrieving questionnaire questions: {e}")
            return pd.DataFrame(columns=['number', 'Question'])
        finally:
            conn.close()

    def delete_questionnaire(self, questionnaire_name):
        """
        Delete a questionnaire and its associated questions from the database.

        Args:
        questionnaire_name (str): The name of the questionnaire to delete.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Start a transaction
            cursor.execute("BEGIN TRANSACTION")

            # First delete all associated questions
            cursor.execute("DELETE FROM questionnaire_questions WHERE questionnaire_name = ?", 
                          (questionnaire_name,))

            # Then delete the questionnaire itself
            cursor.execute("DELETE FROM questionnaires WHERE name = ?", 
                          (questionnaire_name,))

            # Commit the transaction
            cursor.execute("COMMIT")
            return True

        except sqlite3.Error as e:
            # Rollback in case of error
            cursor.execute("ROLLBACK")
            st.error(f"Error deleting questionnaire: {e}")
            return False
        finally:
            conn.close()

    def get_questions(self, questionnaire_name):
        """
        Get all questions for a specific questionnaire
        """
        conn = self._get_connection()
        try:
            query = """
                SELECT question_id as q_id, question as question_text
                FROM questions
                WHERE questionnaire_name =?
                ORDER BY question_id
            """
            df = pd.read_sql_query(query, conn, params=(questionnaire_name,))

            if not df.empty:
                return df
            return pd.DataFrame(columns=['q_id', 'question_text'])
        except Exception as e:
            st.error(f"Error retrieving questions: {e}")
            return pd.DataFrame(columns=['q_id', 'question_text'])
        finally:
            conn.close()
    
    
    def insert_question(self, questionnaire_name, identifier, question):
        """
        Insert a single question into the database.
        
        Args:
            questionnaire_name (str): Name of the questionnaire
            identifier (str): Question identifier provided by user
            question (str): The question text
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO questionnaire_questions 
                (questionnaire_name, identifier, question)
                VALUES (?, ?, ?)
            ''', (questionnaire_name, str(identifier), question))
            conn.commit()
            return True
        except sqlite3.Error as e:
            st.error(f"Error inserting question: {e}")
            return False
        finally:
            conn.close()

    def custom_sort_key(self, index):
        """
        Create a custom sorting key for questionnaire indices.

        Args:
        index (str): The index string to be converted into a sorting key.

        Returns:
        list: A list of parts, with numeric parts converted to integers for proper sorting.
        """
        parts = str(index).split('.')
        return [int(part) if part.isdigit() else part for part in parts]

    def save_questions(self, questionnaire_name):
        """
        Save multiple questions for a questionnaire.
        
        Args:
            questionnaire_name (str): Name of the questionnaire
            questions (list): List of question texts
        """
        # First, delete existing questions for this questionnaire
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM questionnaire_questions WHERE questionnaire_name = ?", 
                         (questionnaire_name,))
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Error saving questions: {e}")
            return False
        finally:
            conn.close()

    def save_questions_from_csv(self, questionnaire_name, questions_df):
        """
        Save questions from a CSV file to the database.
        Takes first column as identifier and second column as question.

        Args:
            questionnaire_name (str): Name of the questionnaire
            questions_df (pd.DataFrame): DataFrame containing questions data
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Delete existing questions for this questionnaire
            cursor.execute("DELETE FROM questionnaire_questions WHERE questionnaire_name = ?", 
                         (questionnaire_name,))

            # Use first column as identifier and second column as question
            identifier_col = questions_df.columns[0]
            question_col = questions_df.columns[1]

            # Sort the DataFrame before inserting
            questions_df['sort_key'] = questions_df[identifier_col].apply(self.custom_sort_key)
            questions_df = questions_df.sort_values(by='sort_key')
            questions_df = questions_df.drop('sort_key', axis=1)

            # Insert new questions
            for _, row in questions_df.iterrows():
                cursor.execute('''
                    INSERT INTO questionnaire_questions 
                    (questionnaire_name, identifier, question)
                    VALUES (?, ?, ?)
                ''', (questionnaire_name, str(row[identifier_col]), row[question_col]))

            conn.commit()
            return True
        except sqlite3.Error as e:
            st.error(f"Error saving questions: {e}")
            return False
        finally:
            conn.close()

    def get_questionnaire_questions(self, questionnaire_name):
        """
        Get questions for a specific questionnaire, sorted by custom index.
        """
        conn = self._get_connection()
        try:
            query = """
                SELECT identifier, question
                FROM questionnaire_questions
                WHERE questionnaire_name = ?
            """
            df = pd.read_sql_query(query, conn, params=(questionnaire_name,))
            
            if not df.empty:
                # Sort the DataFrame using the custom sort key
                df['sort_key'] = df['identifier'].apply(self.custom_sort_key)
                df = df.sort_values(by='sort_key')
                df = df.drop('sort_key', axis=1)  # Remove the temporary sorting column
            
            return df
        except Exception as e:
            st.error(f"Error retrieving questionnaire questions: {e}")
            return pd.DataFrame(columns=['identifier', 'question'])
        finally:
            conn.close()


    def get_categories(self):
        """
        Get all categories
        """
        conn = self._get_connection()
        try:
            query = "SELECT categories FROM categories"
            df = pd.read_sql_query(query, conn)
            return df['categories'].tolist()
        except Exception as e:
            st.error(f"Error retrieving categories: {e}")
            return []
        finally:
            conn.close()

    def get_all_reports(self):
        """Fetch all reports from the database."""
        conn = self._get_connection()
        try:
            query = """
                SELECT id, project, questionnaire, name, num_docs
                FROM reports
            """
            return pd.read_sql_query(query, conn)
        except Exception as e:
            st.error(f"Error retrieving reports: {e}")
            return pd.DataFrame(columns=['id', 'project', 'questionnaire', 'name', 'num_docs'])
        finally:
            conn.close()            
                
    def create_report(self, project, questionnaire, name, num_docs):
        """Create a new report entry in the database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
            INSERT INTO reports (project, questionnaire, name, num_docs)
            VALUES (?, ?, ?, ?)
            """
            cursor.execute(query, (project, questionnaire, name, num_docs))
            report_id = cursor.lastrowid
            conn.commit()
            return report_id
        except sqlite3.Error as e:
            st.error(f"Error creating report: {e}")
            return None
        finally:
            conn.close()

    def get_report_details(self, report_id):
        """Fetch details of a specific report."""
        conn = self._get_connection()
        try:
            query = """
            SELECT project, questionnaire, name, num_docs
            FROM reports
            WHERE id = ?
            """
            df = pd.read_sql_query(query, conn, params=(report_id,))
            return df.iloc[0] if not df.empty else None
        except Exception as e:
            st.error(f"Error retrieving report details: {e}")
            return None
        finally:
            conn.close()

    def get_assigned_documents(self, report_id):
        """Get assigned documents for a report."""
        conn = self._get_connection()
        try:
            query = """
            SELECT content FROM report_documents
            WHERE report_id = ? AND type = 'assigned'
            """
            result = pd.read_sql_query(query, conn, params=(report_id,))
            return json.loads(result['content'][0]) if not result.empty else []
        except Exception as e:
            st.error(f"Error retrieving assigned documents: {e}")
            return []
        finally:
            conn.close()

    def get_included_documents(self, report_id):
        """Get included documents for a report."""
        conn = self._get_connection()
        try:
            query = """
            SELECT content FROM report_documents
            WHERE report_id = ? AND type = 'included'
            """
            result = pd.read_sql_query(query, conn, params=(report_id,))
            return json.loads(result['content'][0]) if not result.empty else []
        except Exception as e:
            st.error(f"Error retrieving included documents: {e}")
            return []

    def save_assigned_documents(self, report_id, doc_titles):
        """Save assigned documents for a report."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
            INSERT INTO report_documents (report_id, type, content)
            VALUES (?, 'assigned', ?)
            """
            cursor.execute(query, (report_id, json.dumps(doc_titles)))
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Error saving assigned documents: {e}")
        finally:
            conn.close()

    def save_included_documents(self, report_id, docs):
        """Save included documents for a report."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
            INSERT INTO report_documents (report_id, type, content)
            VALUES (?, 'included', ?)
            """
            cursor.execute(query, (report_id, json.dumps(docs)))
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Error saving included documents: {e}")
        finally:
            conn.close()

    def delete_questions_from_db(self, questionnaire_name, selected_questions):
        """
        Delete selected questions from a questionnaire.

        Args:
            questionnaire_name (str): Name of the questionnaire
            selected_questions (list): List of dictionaries containing selected question data
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if isinstance(selected_questions, pd.DataFrame):
                rows_to_process = selected_questions
            else:
                rows_to_process = pd.DataFrame(selected_questions)

            if 'identifier' in rows_to_process.columns:
                deleted_questions = []
                for identifier in rows_to_process['identifier']:
                    cursor.execute("""
                        DELETE FROM questionnaire_questions 
                        WHERE questionnaire_name = ? AND identifier = ?
                    """, (questionnaire_name, identifier))
                    deleted_questions.append(identifier)

                if deleted_questions:
                    conn.commit()
                    st.success(f"Successfully deleted questions: {', '.join(deleted_questions)}")
                else:
                    st.warning("No questions were deleted.")
            else:
                st.error(f"Could not find identifier column. Available columns: {rows_to_process.columns.tolist()}")

        except Exception as e:
            st.error(f"Error deleting questions: {str(e)}")
            st.write("Error details:", type(e).__name__)
        finally:
            conn.close()

    def update_questionnaire_completion(self, questions_df, report_id):
        """Update questionnaire completion data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Insert empty responses for each question with both question_id and question_text
            for _, row in questions_df.iterrows():
                cursor.execute("""
                    INSERT INTO questionnaire_responses 
                    (report_id, question_id, question_text, answer, reference)
                    VALUES (?, ?, ?, ?, ?)
                """, (report_id, row['identifier'], row['question'], '', ''))

            conn.commit()
            return questions_df
        except sqlite3.Error as e:
            st.error(f"Error updating questionnaire completion: {e}")
            return None
        finally:
            conn.close()


    def get_connection(self):
        """
        Returns a new connection each time it's called
        """
        return self._get_connection()

# Create a single instance of the database manager
db_manager = DatabaseManager()