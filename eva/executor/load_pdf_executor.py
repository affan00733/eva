# coding=utf-8
# Copyright 2018-2022 EVA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import pandas as pd

from eva.catalog.catalog_manager import CatalogManager
from eva.executor.abstract_executor import AbstractExecutor
from eva.expression.tuple_value_expression import TupleValueExpression
from eva.models.storage.batch import Batch
from eva.plan_nodes.load_data_plan import LoadDataPlan
from eva.readers.pdf_reader import PDFReader
from eva.storage.storage_engine import StorageEngine
from eva.utils.logging_manager import logger


class LoadPDFExecutor(AbstractExecutor):
    def __init__(self, node: LoadDataPlan):
        super().__init__(node)
        self.catalog = CatalogManager()
        self.media_type = self.node.file_options["file_format"]

    def exec(self, *args, **kwargs):
        """
        Read the input csv file using pandas and persist data
        using storage engine
        """

        # Check table existence
        table_info = self.node.table_info
        database_name = table_info.database_name
        table_name = table_info.table_name
        table_obj = self.catalog.get_table_catalog_entry(
            table_name,
            database_name,
        )
        do_create = False
        if table_obj:
            msg = f"Adding to an existing table {table_name}."
            logger.info(msg)
        # Create the catalog entry
        else:
            table_obj = (
                self.catalog.create_and_insert_multimedia_table_catalog_entry(
                    table_name, self.media_type
                )
            )
            do_create = True

        # Get the column information
        column_list = []
        for column in table_obj.columns:
            column_list.append(
                TupleValueExpression(
                    col_name=column.name,
                    table_alias=table_obj.name.lower(),
                    col_object=column,
                )
            )

        # Read the PDF file
        # in the column to the desired type
        pdf_reader = PDFReader(
            self.node.file_path,
            # column_list=column_list,
            batch_mem_size=self.node.batch_mem_size,
        )

        storage_engine = StorageEngine.factory(table_obj)
        if do_create:
            storage_engine.create(table_obj)
        # write with storage engine in batches
        num_loaded_frames = 0
        for batch in pdf_reader.read():
            storage_engine.write(table_obj, batch)
            num_loaded_frames += len(batch)
            break

        # yield result
        df_yield_result = Batch(
            pd.DataFrame(
                {
                    "PDF": str(self.node.file_path),
                    "Number of loaded frames": num_loaded_frames,
                },
                index=[0],
            )
        )

        yield df_yield_result