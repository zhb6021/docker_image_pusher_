import os
import re
import subprocess

def run_command(command):
    """运行命令并捕获输出"""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Command failed: {command}\nError: {result.stderr}")
    return result.stdout.strip()

def parse_image_info(image):
    """解析镜像信息，返回命名空间、镜像名和版本号"""
    parts = image.split('/')
    if len(parts) == 3:
        name_space, image_name_tag = parts[1], parts[2]
    elif len(parts) == 2:
        name_space, image_name_tag = parts[0], parts[1]
    else:
        name_space, image_name_tag = "", parts[0]
    
    image_name, tag = image_name_tag.split(':') if ':' in image_name_tag else (image_name_tag, "")
    return name_space, image_name, tag

def sanitize_tag(tag):
    """将tag中的非法字符替换为允许的字符"""
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', tag)

def main():
    # 登录阿里云容器镜像服务
    run_command(f"docker login -u {os.getenv('ALIYUN_REGISTRY_USER')} -p {os.getenv('ALIYUN_REGISTRY_PASSWORD')} {os.getenv('ALIYUN_REGISTRY')}")

    # 数据预处理，判断镜像是否重名
    duplicate_images = {}
    temp_map = {}
    with open("images.txt", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            image = line.split()[-1].split('@')[0]  # 获取镜像完整名称并去除@sha256等字符
            name_space, image_name, _ = parse_image_info(image)
            
            if image_name in temp_map and temp_map[image_name] != name_space:
                duplicate_images[image_name] = True
            else:
                temp_map[image_name] = name_space

    # 处理镜像
    with open("images.txt", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            platform = re.search(r"--platform\s*=\s*([^ ]+)", line)
            platform_prefix = sanitize_tag(platform.group(1).replace('/', '_')) if platform else ""
            
            image = line.split()[-1].split('@')[0]  # 获取镜像完整名称并去除@sha256等字符
            name_space, image_name, tag = parse_image_info(image)
            
            name_space_prefix = sanitize_tag(name_space) if image_name in duplicate_images and name_space else ""
            
            # 生成新的tag
            new_tag_parts = [tag] if tag else []
            if platform_prefix:
                new_tag_parts.append(platform_prefix)
            if name_space_prefix:
                new_tag_parts.append(name_space_prefix)
            new_tag = '_'.join(new_tag_parts)
            
            new_image = f"{os.getenv('ALIYUN_REGISTRY')}/{os.getenv('ALIYUN_NAME_SPACE')}/{image_name}:{new_tag}"
            
            # 拉取、标记、推送镜像
            run_command(f"docker pull {image}")
            run_command(f"docker tag {image} {new_image}")
            run_command(f"docker push {new_image}")
            
            # 清理磁盘空间
            print("开始清理磁盘空间")
            print("=" * 70)
            run_command("df -hT")
            print("=" * 70)
            run_command(f"docker rmi {image}")
            run_command(f"docker rmi {new_image}")
            print("磁盘空间清理完毕")
            print("=" * 70)
            run_command("df -hT")
            print("=" * 70)

if __name__ == "__main__":
    main()