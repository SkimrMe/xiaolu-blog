// 小绿博客 - 主题管理器
// 职责：读取 js/themes/ 下各主题文件注册的定义（window.BLOG_THEMES），
//       生成主题切换器、切换主题、驱动飘落 emoji 动画。
// 各主题的配色在 css/themes.css，飘落表情等 JS 侧定义在 js/themes/<主题名>.js。
document.addEventListener('DOMContentLoaded', function() {
    // ========== 主题注册表（由各主题文件填充） ==========
    const registry = window.BLOG_THEMES || {};
    // 兜底：主题文件加载失败时至少保证经典绿可用
    if (!registry['green']) {
        registry['green'] = { id: 'green', name: '经典绿', emojis: ['🍃', '🌿', '🍀', '🌱', '☘️', '💚'] };
    }
    const THEMES = Object.values(registry);

    // ========== 飘落 emoji 动画（跟随主题变化） ==========
    const leavesContainer = document.getElementById('leaves');
    let currentEmojis = (registry['green'] || {}).emojis;

    function createLeaf() {
        if (!leavesContainer) return;
        const leaf = document.createElement('div');
        leaf.className = 'leaf';
        leaf.textContent = currentEmojis[Math.floor(Math.random() * currentEmojis.length)];
        leaf.style.left = Math.random() * 100 + 'vw';
        leaf.style.animationDuration = (Math.random() * 5 + 5) + 's';
        leaf.style.fontSize = (Math.random() * 10 + 15) + 'px';
        leavesContainer.appendChild(leaf);

        // 动画结束后移除
        setTimeout(() => {
            leaf.remove();
        }, 10000);
    }

    // 切换主题时更新emoji并清除旧元素
    function updateEmojis(themeId) {
        const theme = registry[themeId] || registry['green'];
        currentEmojis = theme.emojis;
        if (leavesContainer) {
            leavesContainer.querySelectorAll('.leaf').forEach(el => el.remove());
        }
    }

    if (leavesContainer) {
        // 定期生成
        setInterval(createLeaf, 800);
        // 初始生成几个
        for (let i = 0; i < 5; i++) {
            setTimeout(createLeaf, i * 200);
        }
    }

    // ========== 主题切换功能 ==========
    // 创建主题切换器
    const switcher = document.createElement('div');
    switcher.className = 'theme-switcher';
    switcher.innerHTML = THEMES.map(t =>
        `<button class="theme-btn" data-theme="${t.id}" title="${t.name}"></button>`
    ).join('');
    document.body.appendChild(switcher);

    // 切换主题
    function setTheme(themeId) {
        // 移除所有主题类
        document.body.classList.remove('theme-vaporwave', 'theme-frutiger', 'theme-win98', 'theme-pixel');
        // 添加选中主题类（green是默认，不需要class）
        if (themeId && themeId !== 'green') {
            document.body.classList.add(`theme-${themeId}`);
        }
        // 保存到localStorage
        localStorage.setItem('blog-theme', themeId || 'green');
        // 更新按钮状态
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.theme === (themeId || 'green'));
        });
        // 更新飘落emoji
        updateEmojis(themeId || 'green');
    }

    // 绑定按钮点击
    switcher.querySelectorAll('.theme-btn').forEach(btn => {
        btn.addEventListener('click', () => setTheme(btn.dataset.theme));
    });

    // 加载保存的主题
    const savedTheme = localStorage.getItem('blog-theme') || 'green';
    setTheme(registry[savedTheme] ? savedTheme : 'green');
});
