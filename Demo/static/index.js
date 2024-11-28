document.addEventListener('DOMContentLoaded', () => {
    // 현재 URL 경로 확인
    const currentPath = window.location.pathname;
  
    // index.html 전용 코드
    if (currentPath === "/") {
      const myFridgeButton = document.getElementById("my-fridge-button");
      const recipeButton = document.getElementById("recipe-button");
      const quizButton = document.getElementById("quiz-button");
      const chatbotButton = document.getElementById("chatbot-button");
  
      // 버튼 확인 및 이벤트 리스너 추가
      if (myFridgeButton) {
        myFridgeButton.addEventListener("click", () => {
          window.location.href = "/myFridge";
        });
      }
  
      if (recipeButton) {
        recipeButton.addEventListener("click", () => {
          window.location.href = "/recipe";
        });
      }
  
      if (quizButton) {
        quizButton.addEventListener("click", () => {
          window.location.href = "/quiz";
        });
      }
  
      if (chatbotButton) {
        chatbotButton.addEventListener("click", () => {
          window.location.href = "/chatbot";
        });
      }
  
      console.log("index.html용 버튼 이벤트 리스너 설정 완료");
    }
  });
  