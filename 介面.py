<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RC Coffee Mascot Animation</title>
    <style>
        :root {
            --coffee-color: #4b3022; /* 咖啡色 */
        }

        body {
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-color: #f5f5f5;
            cursor: pointer;
            overflow: hidden;
            font-family: Arial, sans-serif;
        }

        .container {
            position: relative;
            width: 400px;
            height: 400px;
        }

        /* 咖啡杯底層 */
        .cup-container {
            position: absolute;
            bottom: 50px;
            left: 50%;
            transform: translateX(-50%);
            width: 300px;
            z-index: 10;
        }

        .cup-img {
            width: 100%;
            display: block;
        }

        /* 遮罩區域：確保液體和人物只在杯內顯示 */
        .mask-area {
            position: absolute;
            bottom: 85px; /* 調整至杯口位置 */
            left: 50%;
            transform: translateX(-50%);
            width: 240px; /* 略小於杯子寬度 */
            height: 150px;
            overflow: hidden;
            z-index: 5;
            /* 這裡設定一個橢圓形的遮罩，模擬杯口內圈 */
            clip-path: ellipse(50% 40% at 50% 100%); 
        }

        /* 咖啡液體 */
        .coffee-liquid {
            position: absolute;
            bottom: -100%; /* 一開始在下方 */
            left: 0;
            width: 100%;
            height: 100%;
            background-color: var(--coffee-color);
            transition: bottom 2s ease-out;
        }

        /* 人物 (貓或嬰兒) */
        .mascot {
            position: absolute;
            bottom: -150px;
            left: 50%;
            transform: translateX(-50%);
            width: 180px;
            transition: bottom 2s ease-out;
        }

        /* 噴濺效果 (嬰兒專用) */
        .splash {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            opacity: 0;
            pointer-events: none;
            z-index: 15;
        }

        /* 對話框 */
        .bubble {
            position: absolute;
            top: -50px;
            right: -20px;
            background: white;
            border: 2px solid #333;
            border-radius: 20px;
            padding: 10px 20px;
            opacity: 0;
            transform: scale(0);
            transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 20;
        }

        .active .coffee-liquid { bottom: 0; }
        .active .mascot { bottom: -20px; }
        .active .bubble { opacity: 1; transform: scale(1); }
        .active .splash { animation: splashFade 1s forwards; }

        @keyframes splashFade {
            0% { opacity: 0; transform: scale(0.5); }
            50% { opacity: 1; transform: scale(1.1); }
            100% { opacity: 0; transform: scale(1.2); }
        }

    </style>
</head>
<body onclick="startAnimation()">

    <div class="container" id="mainContainer">
        <div class="mask-area">
            <div class="coffee-liquid" id="liquid"></div>
            <img src="baby.png" class="mascot" id="mascotImg">
        </div>

        <div class="cup-container">
            <img src="cup.png" class="cup-img">
            <img src="splash.png" class="splash" id="splash">
        </div>

        <div class="bubble" id="bubble">
            建議：喝杯咖啡休息一下吧！
        </div>
    </div>

    <script>
        let isAnimated = false;

        function startAnimation() {
            if (isAnimated) return;
            isAnimated = true;

            const container = document.getElementById('mainContainer');
            const mascot = document.getElementById('mascotImg');
            
            // 隨機決定出現貓還是嬰兒
            const isBaby = Math.random() > 0.5;
            
            if (isBaby) {
                mascot.src = "baby.png";
                // 嬰兒會有噴濺效果
                container.classList.add('active');
            } else {
                mascot.src = "cat.png";
                // 貓的話可以設定延遲讓頭慢一點出來(CSS transition 處理)
                container.classList.add('active');
            }
        }
    </script>
</body>
</html>