// 小绿博客脚本 - 通用交互（平滑滚动、随机小绿图片）
// 注意：飘落emoji动画与主题切换逻辑已拆分到 js/theme-manager.js，
//       各主题的表情定义在 js/themes/<主题名>.js，按页面引入即可。
document.addEventListener('DOMContentLoaded', function() {
    // 带锚点的链接平滑滚动（页面内跳转使用）
    document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    console.log('%c🌱 小绿的博客加载完成啦！', 'color: #228B22; font-size: 16px; font-weight: bold;');
    console.log('%c绿色上网，花季护航 💚', 'color: #32CD32; font-size: 14px;');

    // ========== 随机小绿图片功能（对接 greendam.icu 图库）==========
    // 图库来源：https://greendam.icu/ - 数百张绿坝娘同人图
    const GREENDAM_API = 'https://greendam.icu/';
    const IMAGE_FOLDER = GREENDAM_API + 'images/';
    const IMAGES_JS_URL = GREENDAM_API + 'js/images.js';

    let xiaoluImages = [
        // 兜底本地图片
        'img/gallery/xiaolu_avatar.jpg',
        'img/gallery/lvba_1.jpg',
        'img/gallery/lvba_2.jpg'
    ];

    let currentImageIndex = 0;
    const randomImageEl = document.getElementById('randomXiaoluImage');
    const refreshBtn = document.getElementById('refreshImageBtn');
    const imageInfoEl = document.getElementById('imageInfo');

    // 解析文件名：作者-日期-标题.jpg（来自greendam.icu的命名规范）
    function parseFileName(filename) {
        const name = filename.replace(/\.[^.]+$/, '');
        const parts = name.split('-');
        let author = '', dateStr = '', title = '';

        if (parts.length > 0) author = parts[0];
        const second = parts[1];
        if (/^\d{4,8}$/.test(second)) {
            dateStr = second;
            title = parts.slice(2).join('-');
        } else {
            title = parts.slice(1).join('-');
        }

        let dateFormatted = '';
        if (dateStr) {
            const d = dateStr.replace(/[^\d]/g, '');
            if (d.length === 8) dateFormatted = `${d.slice(0,4)}年${d.slice(4,6)}月${d.slice(6,8)}日`;
            else if (d.length === 6) dateFormatted = `${d.slice(0,4)}年${d.slice(4,6)}月`;
            else if (d.length === 4) dateFormatted = `${d}年`;
        }

        return { author, date: dateFormatted, title: title || '' };
    }

    // 更新图片信息显示
    function updateImageInfo(filename) {
        if (!imageInfoEl) return;
        const { author, date } = parseFileName(filename);
        let infoText = '';
        if (author) infoText += `作者：${author}`;
        if (date) infoText += infoText ? ` · ${date}` : date;
        if (infoText) {
            imageInfoEl.textContent = infoText;
            imageInfoEl.style.display = 'block';
        } else {
            imageInfoEl.style.display = 'none';
        }
    }

    function getRandomImage() {
        // 如果页面上没有随机图片元素（非首页），直接返回
        if (!randomImageEl) return;
        let newIndex;
        do {
            newIndex = Math.floor(Math.random() * xiaoluImages.length);
        } while (newIndex === currentImageIndex && xiaoluImages.length > 1);

        currentImageIndex = newIndex;
        let imgUrl = xiaoluImages[currentImageIndex];

        // 如果是greendam的图片，加上完整路径
        if (!imgUrl.startsWith('img/')) {
            imgUrl = IMAGE_FOLDER + encodeURIComponent(imgUrl);
            updateImageInfo(xiaoluImages[currentImageIndex]);
        } else {
            if (imageInfoEl) imageInfoEl.style.display = 'none';
        }

        // 添加淡入动画
        randomImageEl.style.opacity = '0';
        setTimeout(() => {
            randomImageEl.src = imgUrl;
            randomImageEl.style.opacity = '1';
        }, 200);
    }

    // 尝试从greendam.icu加载完整图片列表
    async function loadGreendamImages() {
        try {
            const response = await fetch(IMAGES_JS_URL);
            if (!response.ok) throw new Error('Failed to load');
            const text = await response.text();

            // 提取IMAGES数组
            const match = text.match(/const IMAGES = \[([\s\S]*?)\];/);
            if (match) {
                // 安全解析数组内容
                const arrayContent = match[1];
                const urls = arrayContent.match(/'([^']+)'/g)?.map(s => s.slice(1, -1)) || [];
                if (urls.length > 0) {
                    xiaoluImages = urls;
                    console.log(`%c✅ 已加载 greendam.icu 图库，共 ${urls.length} 张图片`, 'color: #228B22;');
                    // 加载完后刷新一张
                    getRandomImage();
                }
            }
        } catch (e) {
            console.log('%c⚠️ greendam.icu 图库加载失败，使用本地图片', 'color: #ff6b9d;');
        }
    }

    // 初始化
    getRandomImage();
    loadGreendamImages();

    // 点击按钮刷新
    if (refreshBtn) {
        refreshBtn.addEventListener('click', getRandomImage);
    }

    // 点击图片也可以刷新
    if (randomImageEl) {
        randomImageEl.addEventListener('click', getRandomImage);
        randomImageEl.style.cursor = 'pointer';
    }

});
