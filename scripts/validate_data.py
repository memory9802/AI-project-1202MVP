#!/usr/bin/env python3
"""
資料驗證工具
檢查 CSV 資料品質：重複 SKU、NULL 值、無效分類

使用方式:
    python scripts/validate_data.py dataset/items.csv
    python scripts/validate_data.py init/uniqlo_175.csv
"""

import pandas as pd
import sys
from pathlib import Path


# 有效的 category 值
VALID_CATEGORIES = ['top', 'bottom', 'outer', 'shoes', 'accessory', '上衣', '下身']

# 有效的 gender 值
VALID_GENDERS = ['男', '女', '-']

# 有效的 length 值
VALID_LENGTHS = ['長', '短', '-']


def validate_csv(file_path: str) -> dict:
    """
    驗證 CSV 資料品質
    
    Args:
        file_path: CSV 檔案路徑
        
    Returns:
        dict: 驗證結果
            {
                'valid': bool,
                'issues': list of dict,
                'summary': dict
            }
    """
    if not Path(file_path).exists():
        return {
            'valid': False,
            'issues': [{'type': 'FILE_NOT_FOUND', 'message': f'找不到檔案: {file_path}'}],
            'summary': {}
        }
    
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return {
            'valid': False,
            'issues': [{'type': 'READ_ERROR', 'message': f'讀取失敗: {e}'}],
            'summary': {}
        }
    
    issues = []
    
    # ==================== 檢查 1: 重複的 SKU ====================
    if 'sku' in df.columns:
        duplicates = df[df.duplicated(subset=['sku'], keep=False)]
        if not duplicates.empty:
            dup_skus = duplicates['sku'].unique().tolist()
            issues.append({
                'type': 'DUPLICATE_SKU',
                'severity': 'ERROR',
                'count': len(duplicates),
                'unique_count': len(dup_skus),
                'details': dup_skus[:10],  # 只顯示前10個
                'message': f'發現 {len(dup_skus)} 個重複的 SKU (共 {len(duplicates)} 筆資料)'
            })
    
    # ==================== 檢查 2: NULL 值 ====================
    critical_columns = ['sku', 'name', 'category']
    for col in critical_columns:
        if col in df.columns:
            null_count = df[col].isnull().sum()
            # 也檢查 '-' 字串
            dash_count = (df[col] == '-').sum() if col == 'category' else 0
            
            if null_count > 0 or dash_count > 0:
                total_invalid = null_count + dash_count
                issues.append({
                    'type': 'NULL_VALUE',
                    'severity': 'ERROR' if col in ['sku', 'category'] else 'WARNING',
                    'column': col,
                    'null_count': null_count,
                    'dash_count': dash_count,
                    'total': total_invalid,
                    'message': f'{col} 欄位有 {total_invalid} 筆無效值 (NULL: {null_count}, "-": {dash_count})'
                })
    
    # ==================== 檢查 3: 無效的 category 值 ====================
    if 'category' in df.columns:
        invalid_categories = df[~df['category'].isin(VALID_CATEGORIES) & df['category'].notnull()]
        if not invalid_categories.empty:
            unique_invalid = invalid_categories['category'].unique().tolist()
            issues.append({
                'type': 'INVALID_CATEGORY',
                'severity': 'WARNING',
                'count': len(invalid_categories),
                'details': unique_invalid,
                'message': f'發現 {len(invalid_categories)} 筆無效的 category 值: {unique_invalid}'
            })
    
    # ==================== 檢查 4: 無效的 gender 值 ====================
    if 'gender' in df.columns:
        invalid_genders = df[~df['gender'].isin(VALID_GENDERS) & df['gender'].notnull()]
        if not invalid_genders.empty:
            unique_invalid = invalid_genders['gender'].unique().tolist()
            issues.append({
                'type': 'INVALID_GENDER',
                'severity': 'WARNING',
                'count': len(invalid_genders),
                'details': unique_invalid,
                'message': f'發現 {len(invalid_genders)} 筆無效的 gender 值: {unique_invalid}'
            })
    
    # ==================== 檢查 5: 無效的 length 值 ====================
    if 'length' in df.columns:
        invalid_lengths = df[~df['length'].isin(VALID_LENGTHS) & df['length'].notnull()]
        if not invalid_lengths.empty:
            unique_invalid = invalid_lengths['length'].unique().tolist()
            issues.append({
                'type': 'INVALID_LENGTH',
                'severity': 'WARNING',
                'count': len(invalid_lengths),
                'details': unique_invalid,
                'message': f'發現 {len(invalid_lengths)} 筆無效的 length 值: {unique_invalid}'
            })
    
    # ==================== 統計資訊 ====================
    summary = {
        'total_rows': len(df),
        'columns': df.columns.tolist(),
        'unique_skus': df['sku'].nunique() if 'sku' in df.columns else 0,
        'has_errors': any(issue['severity'] == 'ERROR' for issue in issues),
        'has_warnings': any(issue['severity'] == 'WARNING' for issue in issues)
    }
    
    # 判斷是否通過驗證
    valid = not summary['has_errors']
    
    return {
        'valid': valid,
        'issues': issues,
        'summary': summary
    }


def print_report(result: dict, file_path: str):
    """
    列印驗證報告
    
    Args:
        result: validate_csv 的回傳結果
        file_path: CSV 檔案路徑
    """
    print("=" * 80)
    print("📋 資料驗證報告")
    print("=" * 80)
    print(f"\n檔案: {file_path}")
    
    summary = result.get('summary', {})
    print(f"總筆數: {summary.get('total_rows', 0)}")
    print(f"唯一 SKU: {summary.get('unique_skus', 0)}")
    print(f"欄位: {', '.join(summary.get('columns', []))}")
    
    issues = result.get('issues', [])
    
    if not issues:
        print("\n" + "=" * 80)
        print("✅ 資料驗證通過！沒有發現任何問題。")
        print("=" * 80)
        return
    
    # 分類顯示問題
    errors = [issue for issue in issues if issue['severity'] == 'ERROR']
    warnings = [issue for issue in issues if issue['severity'] == 'WARNING']
    
    if errors:
        print("\n" + "=" * 80)
        print("❌ 嚴重錯誤 (必須修復)")
        print("=" * 80)
        for issue in errors:
            print(f"\n{issue['type']}:")
            print(f"  {issue['message']}")
            if 'details' in issue and issue['details']:
                print(f"  範例: {issue['details'][:5]}")
    
    if warnings:
        print("\n" + "=" * 80)
        print("⚠️  警告 (建議修復)")
        print("=" * 80)
        for issue in warnings:
            print(f"\n{issue['type']}:")
            print(f"  {issue['message']}")
            if 'details' in issue and issue['details']:
                print(f"  範例: {issue['details'][:5]}")
    
    print("\n" + "=" * 80)
    if result['valid']:
        print("⚠️  驗證通過，但有警告")
    else:
        print("❌ 驗證失敗，請修復錯誤後重試")
    print("=" * 80)
    
    # 修復建議
    if errors:
        print("\n💡 修復建議:")
        if any(issue['type'] == 'DUPLICATE_SKU' for issue in errors):
            print("  1. 執行去重: df.drop_duplicates(subset=['sku'], keep='first')")
        if any(issue['type'] == 'NULL_VALUE' and issue['column'] == 'category' for issue in errors):
            print("  2. 補充 category: 使用 auto_fill_category() 函數")
        if any(issue['type'] == 'NULL_VALUE' and issue['column'] == 'sku' for issue in errors):
            print("  3. 刪除無效行: df = df[df['sku'].notnull()]")


def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("使用方式:")
        print("  python scripts/validate_data.py <csv_file>")
        print("\n範例:")
        print("  python scripts/validate_data.py dataset/items.csv")
        print("  python scripts/validate_data.py init/uniqlo_175.csv")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # 執行驗證
    result = validate_csv(file_path)
    
    # 列印報告
    print_report(result, file_path)
    
    # 回傳 exit code
    if result['valid']:
        sys.exit(0)  # 通過
    else:
        sys.exit(1)  # 失敗


if __name__ == '__main__':
    main()
