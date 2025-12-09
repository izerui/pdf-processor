import pymupdf
import pandas as pd
import os
import argparse
from typing import List, Dict, Any


def extract_target_tables_from_pdf(pdf_path: str, target_headers: List[str]) -> List[Dict[str, Any]]:
    """
    从 PDF 文件中提取包含特定表头的表格

    Args:
        pdf_path: PDF 文件路径
        target_headers: 需要匹配的表头列表

    Returns:
        包含匹配表格的列表
    """
    doc = pymupdf.open(pdf_path)
    all_tables = []

    print(f"处理 PDF: {pdf_path}")
    print(f"总页数: {doc.page_count}")

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        # 获取页面中的表格
        table_finder = page.find_tables()
        tables = table_finder.tables
        
        print(f"页面 {page_num + 1}: 找到 {len(tables)} 个表格")

        for table_idx, table in enumerate(tables):
            # 获取表格数据
            try:
                data = table.extract()
                if data and len(data) > 0:
                    # 清理表头中的换行符，用于匹配
                    cleaned_headers_for_match = [header.replace('\n', '') if header else '' for header in data[0]]
                    # 检查第一行是否包含目标表头
                    if len(data) > 0 and any(header in cleaned_headers_for_match for header in target_headers):
                        print(f"  表格 {table_idx + 1} 包含目标表头: {data[0]}")
                        
                        # 清理列名中的换行符
                        cleaned_headers = [header.replace('\n', '') if header else '' for header in data[0]]
                        
                        # 第一行作为列名
                        if len(data) > 1:
                            df = pd.DataFrame(data[1:], columns=cleaned_headers)
                        else:
                            df = pd.DataFrame(data)
                            # 如果只有一行数据，也清理列名（如果有列名）
                            if len(df.columns) > 0 and len(df.columns) == len(cleaned_headers):
                                df.columns = cleaned_headers
                        
                        # 添加表格标识信息
                        df['page'] = page_num + 1
                        df['table_index'] = table_idx + 1
                        
                        all_tables.append(df)
                    else:
                        print(f"  表格 {table_idx + 1} 不包含目标表头，跳过")
            except Exception as e:
                print(f"提取表格 {table_idx + 1} 时出错 (页面 {page_num + 1}): {str(e)}")

    doc.close()
    return all_tables


def save_tables_to_excel(tables: List[pd.DataFrame], output_path: str) -> None:
    """
    将每个表格保存到 Excel 文件的独立工作表中

    Args:
        tables: 表格 DataFrame 列表
        output_path: 输出 Excel 文件路径
    """
    print(f"保存 {len(tables)} 个表格到 {output_path}")
    
    # 统计每页的表格数量，用于生成序号
    page_table_counts = {}
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for i, df in enumerate(tables):
            # 获取页码
            page_num = df.iloc[0]['page'] if len(df) > 0 and 'page' in df.columns else "Unknown"
            
            # 统计该页的表格数量
            if page_num not in page_table_counts:
                page_table_counts[page_num] = 1
            else:
                page_table_counts[page_num] += 1
            
            # 创建工作表名称，使用页码和序号
            sheet_name = f"Page_{page_num}_{page_table_counts[page_num]}"
            
            # Excel 工作表名称不能超过31个字符
            sheet_name = sheet_name[:31]
            
            # 写入表格到 Excel（去掉page和table_index列）
            df_to_save = df.drop(columns=['page', 'table_index'], errors='ignore')
            df_to_save.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False
            )
            
            print(f"    保存工作表: {sheet_name}")


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='从 PDF 文件中提取特定表头的表格并合并相同结构的表格')
    parser.add_argument('--files', nargs='+', help='要处理的 PDF 文件')
    parser.add_argument('--output', default='output', help='Excel 文件输出目录')
    parser.add_argument('--all', action='store_true', help='处理当前目录中的所有 PDF 文件')
    parser.add_argument('--headers', nargs='+', default=['课程类别', '课程分类', '课程代码', '课程名称'], 
                        help='需要匹配的表头关键词')

    args = parser.parse_args()

    # 获取当前目录用于相对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 确保输出目录存在
    output_dir = os.path.join(current_dir, args.output)
    os.makedirs(output_dir, exist_ok=True)

    # 确定要处理的文件
    if args.files:
        # 处理指定的文件（转换为绝对路径）
        pdf_files = [os.path.join(current_dir, f) if not os.path.isabs(f) else f for f in args.files]
    else:
        # 默认处理当前目录中的所有 PDF 文件
        pdf_files = [os.path.join(current_dir, f) for f in os.listdir(current_dir) 
                     if f.lower().endswith('.pdf')]

    print(f"处理 {len(pdf_files)} 个 PDF 文件...")

    # 目标表头
    target_headers = args.headers

    # 处理每个PDF文件，生成对应的Excel文件
    total_tables = 0
    for file_path in pdf_files:
        try:
            if os.path.exists(file_path):
                print(f"\n处理文件: {file_path}")
                
                # 从该PDF文件中提取表格
                tables = extract_target_tables_from_pdf(file_path, target_headers)
                
                if tables:
                    # 获取PDF文件名（不含扩展名）
                    pdf_basename = os.path.splitext(os.path.basename(file_path))[0]
                    excel_filename = f"{pdf_basename}.xlsx"
                    output_path = os.path.join(output_dir, excel_filename)
                    
                    # 保存表格到Excel
                    save_tables_to_excel(tables, output_path)
                    print(f"已保存 {len(tables)} 个表格到 {output_path}")
                    total_tables += len(tables)
                else:
                    print(f"在 {file_path} 中没有找到匹配的表格")
            else:
                print(f"文件不存在: {file_path}")
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {str(e)}")

    # 打印摘要
    print(f"\n摘要:")
    print(f"  总共找到 {total_tables} 个包含目标表头的表格")
    print(f"  每个PDF文件生成对应的Excel文件，表格保存为独立的工作表")


if __name__ == '__main__':
    main()