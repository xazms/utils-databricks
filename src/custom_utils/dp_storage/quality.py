from pyspark.sql.utils import AnalysisException
from custom_utils.helper import get_key_columns_list

def build_duplicate_check_query(view_name: str, key_columns_list: list) -> str:
    """
    Constructs an SQL query to check for duplicates in the dataset.

    Args:
        view_name (str): The name of the temporary view containing the data.
        key_columns_list (list): A list of key columns to check for duplicates.

    Returns:
        str: The constructed SQL query for duplicate checking.
    """
    partition_by_columns = ', '.join(['input_file_name'] + key_columns_list)
    key_columns_str = ', '.join(key_columns_list)

    query = f"""
    SELECT 
        raise_error('ERROR: duplicates in new data for {key_columns_str}') AS error_message, 
        COUNT(*) AS duplicate_count, 
        {', '.join(['input_file_name'] + key_columns_list)}
    FROM {view_name}
    GROUP BY {partition_by_columns}
    HAVING COUNT(*) > 1;
    """
    return query

def check_for_duplicates(query: str, spark, helper=None) -> None:
    """
    Executes the SQL query to check for duplicates and handles the result.

    Args:
        query (str): The SQL query to check for duplicates.
        spark (SparkSession): The active Spark session.
        helper (optional): A logging helper object.

    Raises:
        ValueError: If duplicates are found in the new data.
    """
    if helper:
        helper.write_message(f"Executing duplicate check query: {query}")

    try:
        duplicates_df = spark.sql(query)
        duplicate_count = duplicates_df.count()

        if duplicate_count > 0:
            if helper:
                helper.write_message(f"ERROR: Found {duplicate_count} duplicate records!")
            duplicates_df.show(truncate=False)
            raise ValueError(f"Data Quality Check Failed: Found {duplicate_count} duplicates in the new data.")
        else:
            if helper:
                helper.write_message("Data Quality Check Passed: No duplicates found in the new data.")
    except AnalysisException as e:
        if helper:
            helper.write_message(f"Error executing duplicate check query: {e}")
        raise

def perform_quality_check(spark, key_columns, view_name, helper=None) -> None:
    """
    Performs the quality check for duplicates in the new data.

    Args:
        spark (SparkSession): The active Spark session.
        key_columns (str): A comma-separated string of key columns.
        view_name (str): The name of the temporary view containing the data.
        helper (optional): A logging helper object.
    """
    if not key_columns:
        raise ValueError("ERROR: No KeyColumns provided!")

    # Get the list of key columns
    key_columns_list = get_key_columns_list(key_columns)

    # Build the SQL query for duplicate checking
    query = build_duplicate_check_query(view_name, key_columns_list)

    # Execute the query and handle the results
    check_for_duplicates(query, spark, helper)