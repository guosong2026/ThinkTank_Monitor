#!/usr/bin/env python
"""修复website_configs.py中的函数定义顺序问题"""

import re

def read_file_lines(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.readlines()

def write_file_lines(filepath, lines):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def find_function_def(lines, func_name):
    """查找函数定义的位置"""
    for i, line in enumerate(lines):
        if line.strip().startswith(f'def {func_name}('):
            return i
    return -1

def extract_function(lines, start_idx):
    """从起始位置提取整个函数"""
    if start_idx < 0 or start_idx >= len(lines):
        return None, None
    
    # 查找函数结束位置（下一个def或文件结尾）
    end_idx = start_idx + 1
    while end_idx < len(lines):
        line = lines[end_idx]
        # 如果是空行，继续检查
        if line.strip() == '':
            end_idx += 1
            continue
        # 如果是下一个函数定义
        if line.strip().startswith('def '):
            break
        # 如果是类定义
        if line.strip().startswith('class '):
            break
        # 如果是分区标题
        if line.strip().startswith('# =') and '=' in line:
            # 检查前一行是否是空行
            if end_idx > 0 and lines[end_idx-1].strip() == '':
                # 可能属于这个函数的分区标题
                pass
            else:
                break
        end_idx += 1
    
    # 如果结束位置是空行，需要包含吗？为了格式，我们包含空行直到非空行
    while end_idx < len(lines) and lines[end_idx].strip() == '':
        end_idx += 1
    
    return start_idx, end_idx

def main():
    filepath = 'website_configs.py'
    lines = read_file_lines(filepath)
    
    # 查找需要移动的函数
    funcs_to_move = ['nature_cities_parser', 'world_bank_parser']
    func_blocks = []
    
    for func_name in funcs_to_move:
        start_idx = find_function_def(lines, func_name)
        if start_idx < 0:
            print(f"警告: 未找到函数 {func_name}")
            continue
        
        start, end = extract_function(lines, start_idx)
        if start is None:
            print(f"警告: 无法提取函数 {func_name}")
            continue
        
        func_blocks.append({
            'name': func_name,
            'start': start,
            'end': end,
            'lines': lines[start:end]
        })
        print(f"找到函数 {func_name}: 行 {start+1} 到 {end}")
    
    if not func_blocks:
        print("没有需要移动的函数")
        return
    
    # 按照原始顺序排序（从后往前移除，避免索引变化）
    func_blocks.sort(key=lambda x: x['start'], reverse=True)
    
    # 先移除函数
    for block in func_blocks:
        del lines[block['start']:block['end']]
        print(f"已移除函数 {block['name']}")
    
    # 查找插入位置（在lincoln_institute_parser之后，分区标题之前）
    insert_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == 'def lincoln_institute_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:':
            # 找到这个函数的结束位置
            start, end = extract_function(lines, i)
            if start is not None:
                insert_idx = end
                print(f"找到插入位置: 行 {insert_idx+1} (在 lincoln_institute_parser 之后)")
                break
    
    if insert_idx < 0:
        # 如果找不到，在DEFAULT_WEBSITES之前插入
        for i, line in enumerate(lines):
            if line.strip() == 'DEFAULT_WEBSITES = [':
                insert_idx = i
                print(f"找到插入位置: 行 {insert_idx+1} (在 DEFAULT_WEBSITES 之前)")
                break
    
    if insert_idx < 0:
        print("错误: 找不到插入位置")
        return
    
    # 按照原始顺序插入函数（从前到后）
    func_blocks.sort(key=lambda x: x['start'])
    
    # 在插入位置添加函数
    for block in func_blocks:
        # 添加空行分隔
        if insert_idx > 0 and lines[insert_idx-1].strip() != '':
            lines.insert(insert_idx, '\n')
            insert_idx += 1
        
        lines[insert_idx:insert_idx] = block['lines']
        insert_idx += len(block['lines'])
        print(f"已插入函数 {block['name']}")
    
    # 写入文件
    write_file_lines(filepath, lines)
    print(f"已修复 {filepath}")
    
    # 验证修复
    print("\n验证修复...")
    try:
        # 尝试导入以确保没有语法错误
        import website_configs
        print("✓ 导入成功")
        
        # 检查函数是否可访问
        from website_configs import nature_cities_parser, world_bank_parser
        print("✓ 函数可导入")
        
        # 检查DEFAULT_WEBSITES
        from website_configs import DEFAULT_WEBSITES
        print(f"✓ DEFAULT_WEBSITES 包含 {len(DEFAULT_WEBSITES)} 个网站")
        
        # 检查新网站配置
        nature_config = next((c for c in DEFAULT_WEBSITES if c.name == "Nature Cities"), None)
        world_bank_config = next((c for c in DEFAULT_WEBSITES if c.name == "World Bank"), None)
        
        if nature_config and nature_config.parser_func:
            print("✓ Nature Cities 配置正常")
        else:
            print("✗ Nature Cities 配置有问题")
            
        if world_bank_config and world_bank_config.parser_func:
            print("✓ World Bank 配置正常")
        else:
            print("✗ World Bank 配置有问题")
            
    except Exception as e:
        print(f"✗ 验证失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()