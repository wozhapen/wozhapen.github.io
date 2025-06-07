# encoding: utf-8
# file: md_to_html.py
import pathlib
import mistune
import html
import argparse
import os
import shutil
import sys
import datetime

# 极简 CSS 样式
CSS_STYLE = """
body {
  font-family: "Courier New";
  background-color: #ffffff;
}

/* 简单导航栏样式 */
.navbar {
    font-weight: bold;
    padding: 8px 12px;
    border-bottom: 1px solid #ccc;
    margin-bottom: 15px;
}

/* 链接样式 */
a {
    color: #000;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}
"""

class NavigationManager:
    """管理页面导航栏"""
    def __init__(self, output_dir):
        self.output_dir = pathlib.Path(output_dir).resolve()
        self.top_level_dirs = []
        self.home_link = "index.html"
        
    def add_top_level_dir(self, dir_name):
        """添加顶级目录到导航栏"""
        if dir_name not in self.top_level_dirs:
            self.top_level_dirs.append(dir_name)
    
    def generate_navbar(self, current_path):
        """生成带目录链接的导航栏"""
        # 计算首页路径
        home_path = self.output_dir / self.home_link
        home_rel = os.path.relpath(home_path, current_path.parent)
        
        # 创建目录链接
        dir_links = []
        for dir_name in self.top_level_dirs:
            dir_index = self.output_dir / dir_name / "index.html"
            rel_path = os.path.relpath(dir_index, current_path.parent)
            dir_links.append(f'<a href="{rel_path}">{html.escape(dir_name)}</a>')
        
        return f"""
        <div class="navbar">
            <a href="{home_rel}">首页</a> | 
            {' | '.join(dir_links)}
        </div>"""

def convert_md_to_html(md_path, output_dir, input_root, nav_manager):
    """转换单个Markdown文件为HTML，包含元数据解析"""
    title = md_path.stem  # 默认使用文件名作为标题
    # 读取Markdown内容
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except Exception as e:
        print(f"读取文件错误 {md_path}: {e}", file=sys.stderr)
        return None

    # 转换为HTML
    html_content = mistune.html(md_content)

    # 计算相对路径
    try:
        rel_path = md_path.relative_to(input_root)
    except ValueError:
        rel_path = pathlib.Path(os.path.relpath(md_path, input_root))

    # 构建输出路径
    html_path = output_dir / rel_path.with_suffix('.html')
    html_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 生成导航栏
    navbar = nav_manager.generate_navbar(html_path)

    # 构建 HTML 页面
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{html.escape(title)}</title>
    <style>{CSS_STYLE}</style>
</head>
<body>
    {navbar}
    <div class="content-container">
        {html_content}
    </div>
</body>
</html>"""

    # 写入文件
    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        return html_path.relative_to(output_dir)
    except Exception as e:
        print(f"写入文件错误 {html_path}: {e}", file=sys.stderr)
        return None

def generate_directory_first_index(directory, output_dir, root_dir, input_root, nav_manager):
    """为目录生成索引页（增强版：支持按创建时间排序的文章列表）"""
    index_path = directory / "index.html"

    # 收集所有HTML文件（非索引文件）
    all_htmls = []
    for html_file in pathlib.Path(output_dir).rglob("*.html"):
        if html_file.name == "index.html":
            continue
            
        # 获取对应的Markdown文件路径
        rel_path = html_file.relative_to(output_dir)
        md_file = pathlib.Path(input_root) / rel_path.with_suffix(".md")
        
        if not md_file.exists():
            continue
            
        try:
            # 获取并存储创建时间
            ctime = md_file.stat().st_ctime
            all_htmls.append((html_file, ctime))
        except Exception as e:
            print(f"无法获取时间 {md_file}: {e}")
    
    # 按创建时间倒序排序
    all_htmls.sort(key=lambda x: x[1], reverse=True)
    
    # 生成列表项
    file_list = []
    for html_file, ctime in all_htmls:
        rel_path = os.path.relpath(html_file, directory)
        title = html_file.stem
        time_str = datetime.datetime.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M')
        
        file_list.append(
            f'<li>📄 <a href="{rel_path}">{time_str} {html.escape(title)}</a></li>'
        )
    
    navbar = nav_manager.generate_navbar(index_path)
    file_list_str = '\n            '.join(file_list)
    
    index_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>所有文章</title>
    <style>{CSS_STYLE}</style>
</head>
<body>
    {navbar}
    <div class="content-container">
        <h1>最新文章</h1>
        <ul>
            {file_list_str}
        </ul>
    </div>
</body>
</html>"""
    
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
    except Exception as e:
        print(f"写入索引错误 {index_path}: {e}", file=sys.stderr)
    return

def generate_directory_sub_index(directory, output_dir, root_dir, input_root, nav_manager):
    """为目录生成索引页（增强版：支持按创建时间排序）"""
    index_path = directory / "index.html"
    
    # 收集当前目录下的HTML文件
    html_files = []
    
    # 处理子目录和文件
    try:
        for item in os.listdir(directory):
            item_path = directory / item
            if item_path == index_path:
                continue
                
            if item_path.is_dir():
                dir_index = item_path / "index.html"
                if not dir_index.exists():
                    generate_directory_sub_index(item_path, output_dir, root_dir, input_root, nav_manager)
                
                # 添加目录项
                rel_path = os.path.relpath(dir_index, directory)
                html_files.append((item_path, None))  # 目录没有创建时间
                
            elif item_path.suffix == '.html':
                # 获取对应的Markdown文件路径
                rel_path = item_path.relative_to(output_dir)
                md_file = pathlib.Path(input_root) / rel_path.with_suffix(".md")
                
                if md_file.exists():
                    # 获取并存储创建时间
                    ctime = md_file.stat().st_ctime
                    html_files.append((item_path, ctime))
    except Exception as e:
        print(f"读取目录错误 {directory}: {e}", file=sys.stderr)
        return
    
    # 按创建时间倒序排序（目录排在前面，然后是最新文件）
    html_files.sort(key=lambda x: (x[1] is not None, x[1] if x[1] is not None else 0), reverse=True)
    
    # 生成列表项
    file_list = []
    for item_path, ctime in html_files:
        if item_path.is_dir():
            # 处理目录项
            dir_index = item_path / "index.html"
            rel_path = os.path.relpath(dir_index, directory)
            file_list.append(f'<li>📁 <a href="{rel_path}">{html.escape(item_path.name)}</a></li>')
        else:
            # 处理文件项
            rel_path = os.path.relpath(item_path, directory)
            title = item_path.stem
            time_str = datetime.datetime.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M')
            
            file_list.append(
                f'<li>📄 <a href="{rel_path}">{time_str} {html.escape(title)}</a></li>'
            )
    
    navbar = nav_manager.generate_navbar(index_path)
    
    # 如果是根目录，显示"所有文章"标题，否则显示当前目录名
    if directory == root_dir:
        page_title = "所有文章"
        h1_title = "最新文章"
    else:
        page_title = h1_title = html.escape(directory.relative_to(root_dir).name)
    
    file_list_str = '\n            '.join(file_list)

    index_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{page_title}</title>
    <style>{CSS_STYLE}</style>
</head>
<body>
    {navbar}
    <div class="content-container">
        <h1>{h1_title}</h1>
        <ul>
            {file_list_str}
        </ul>
    </div>
</body>
</html>"""
    
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
    except Exception as e:
        print(f"写入索引错误 {index_path}: {e}", file=sys.stderr)

def find_md_files(root_dir):
    """查找所有Markdown文件"""
    return list(pathlib.Path(root_dir).glob('**/*.md'))

def find_top_level_dirs(input_dir):
    """查找输入目录下的所有顶级目录"""
    input_path = pathlib.Path(input_dir).resolve()
    return [d.name for d in input_path.iterdir() if d.is_dir()]

def copy_asset(output_dir):
    """复制静态资源文件（固定使用脚本同级目录下的css）"""
    # 获取当前脚本所在目录
    script_dir = pathlib.Path(__file__).parent
    asset_source = script_dir / "asset"
    asset_target = pathlib.Path(output_dir) / "assert" 
    
    if asset_source.exists():
        if asset_target.exists():
            shutil.rmtree(asset_target)  # 清除旧文件
        shutil.copytree(asset_source, asset_target)
        print(f"asset资源已复制到: {asset_target}")
    else:
        print(f"警告：源asset目录 {asset_source} 不存在，跳过复制")
def copy_resources(input_dir, output_dir):    
    # 复制文件资源目录
    resource_source = pathlib.Path(input_dir) / "_resources"
    resource_target = pathlib.Path(output_dir) / "_resources"
    
    if resource_source.exists():
        if resource_target.exists():
            shutil.rmtree(resource_target)  # 清除旧文件
        shutil.copytree(resource_source, resource_target)
        print(f"文件资源已复制到: {resource_target}")
    else:
        print(f"警告：源文件目录 {resource_source} 不存在，跳过复制")

def ignore_hidden_and_git(path, files):
    # 排除 .git 文件夹 和 所有以 '.' 开头的隐藏文件/文件夹
    return [os.path.join(path, f) for f in files if f == '.git' or f.startswith('.')]

def safe_rmtree(path, ignore_func):
    """安全删除目录，支持自定义忽略规则"""
    if not os.path.exists(path):
        return
        
    for root, dirs, files in os.walk(path, topdown=True):
        # 调用 ignore_func 获取需要忽略的文件/目录名
        ignored_items = ignore_func(root, dirs + files)

        # 过滤掉需要忽略的子目录和文件
        dirs[:] = [d for d in dirs if os.path.join(root, d) not in ignored_items]
        files[:] = [f for f in files if os.path.join(root, f) not in ignored_items]

        # 删除文件
        for name in files:
            os.remove(os.path.join(root, name))
        
        # 删除目录
        for name in dirs:
            shutil.rmtree(os.path.join(root, name))
def main(input_dir=".", output_dir="html_output"):
    """主处理函数"""
    root_dir = pathlib.Path(input_dir).resolve()
    out_dir = pathlib.Path(output_dir).resolve()
    
    if out_dir.exists():
        print(f"已存在输出目录 {out_dir}，将进行清理")
        safe_rmtree(out_dir, ignore_hidden_and_git)
    out_dir.mkdir(parents=True, exist_ok=True)

    #  复制前端资源
    copy_asset(out_dir)

    #  复制markdown里涉及文件资源
    copy_resources(root_dir, out_dir)
    
    nav_manager = NavigationManager(out_dir)
    
    top_dirs = find_top_level_dirs(root_dir)
    for dir_name in top_dirs:
        if dir_name == "_resources":
           continue
        nav_manager.add_top_level_dir(dir_name)
        print(f"添加导航目录: {dir_name}")
    
    md_files = find_md_files(root_dir)
    print(f"找到 {len(md_files)} 个Markdown文件")
    
    for i, md_file in enumerate(md_files):
        print(f"转换中 ({i+1}/{len(md_files)}): {md_file.relative_to(root_dir)}")
        convert_md_to_html(md_file, out_dir, root_dir, nav_manager)
    
    print("生成目录索引...")
    for item in os.listdir(out_dir):
        # 如果是assert目录则直接返回不处理
        if item == 'asset':
            continue
        if item == '_resources':
            continue

        full_path = os.path.join(out_dir, item)

        if os.path.isdir(full_path):
            dir_path = pathlib.Path(full_path)
            generate_directory_sub_index(dir_path, out_dir, out_dir, root_dir, nav_manager)
    
    generate_directory_first_index(out_dir, out_dir, out_dir, root_dir, nav_manager)

    # 把自己备份一下
    try:
        shutil.copy(__file__, out_dir / 'md_to_html.py')
        print(f"脚本文件已复制到: {out_dir / 'md_to_html.py'}")
    except Exception as e:
        print(f"复制脚本文件失败: {e}", file=sys.stderr)
    
    print(f"\n转换完成！生成文件保存在: {out_dir}")
    print(f"请打开 {out_dir / 'index.html'} 查看文档中心")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="极简Markdown转换工具")
    parser.add_argument("--input", default=".", help="输入目录（默认当前目录）")
    parser.add_argument("--output", default="html_output", help="输出目录（默认'html_output'）")
    args = parser.parse_args()
    
    main(input_dir=args.input, output_dir=args.output)