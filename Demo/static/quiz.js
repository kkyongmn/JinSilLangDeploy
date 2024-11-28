function showExplanation(selectedAnswer) {
    // 정답 및 해설 정보는 서버에서 렌더링된 데이터를 사용
    const explanationBox = document.getElementById("explanation-box");
    const explanationText = document.getElementById("explanation-text");
  
    if (selectedAnswer === correctAnswer) {
      explanationText.innerHTML = "정답입니다! <br>" + explanation;
      explanationBox.style.color = "green"; // 정답일 경우 녹색 표시
    } else {
      explanationText.innerHTML = "오답입니다! <br>" + explanation;
      explanationBox.style.color = "red"; // 오답일 경우 빨간색 표시
    }
  
    explanationBox.style.display = "block";
  }
  
  document.addEventListener("DOMContentLoaded", () => {
    // Back 버튼 동작 구현
    const backButton = document.getElementById("back-button");
    if (backButton) {
      backButton.addEventListener("click", () => {
        window.location.href = "/"; // index.html로 이동
      });
    }
  });
  