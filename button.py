import pygame

# 初始化Pygame
pygame.init()

# 设置窗口参数
window_width = 800
window_height = 600

# 创建窗口对象
window = pygame.display.set_mode((window_width, window_height))
pygame.display.set_caption("Button Example")

# 定义按钮参数
button_data = [
    {"name": "Button1", "rect": pygame.Rect(100, 100, 200, 50), "color": (0, 255, 0)},
    {"name": "Button2", "rect": pygame.Rect(100, 200, 200, 50), "color": (255, 0, 0)},
    {"name": "Button3", "rect": pygame.Rect(100, 300, 200, 50), "color": (0, 0, 255)}
]

# 创建按钮文本
font = pygame.font.Font(None, 36)

# 主循环
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            for button in button_data:
                if button["rect"].collidepoint(event.pos):
                    # 处理按钮点击事件
                    print(f"{button['name']} Clicked!")

    for button in button_data:
        # 检查鼠标位置
        mouse_pos = pygame.mouse.get_pos()
        if button["rect"].collidepoint(mouse_pos):
            button_color = (200, 200, 200)
        else:
            button_color = button["color"]

        # 渲染按钮
        pygame.draw.rect(window, button_color, button["rect"])
        text = font.render(button["name"], True, (0, 0, 0))
        text_rect = text.get_rect(center=button["rect"].center)
        window.blit(text, text_rect)

    pygame.display.flip()

# 退出Pygame
pygame.quit()
