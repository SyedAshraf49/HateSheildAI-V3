const video = document.getElementById("video")

Promise.all([
  faceapi.nets.tinyFaceDetector.loadFromUri("../models"),
  faceapi.nets.faceExpressionNet.loadFromUri("../models")
]).then(startVideo)

function startVideo() {
  navigator.mediaDevices.getUserMedia({ video: {} })
    .then(stream => {
      video.srcObject = stream
    })
    .catch(err => console.error(err))
}

video.addEventListener("play", () => {
  const canvas = faceapi.createCanvasFromMedia(video)
  document.querySelector(".container").append(canvas)

  const displaySize = {
    width: video.width,
    height: video.height
  }

  faceapi.matchDimensions(canvas, displaySize)

  setInterval(async () => {
    const detections = await faceapi
      .detectAllFaces(video, new faceapi.TinyFaceDetectorOptions())
      .withFaceExpressions()

    const resizedDetections = faceapi.resizeResults(detections, displaySize)

    canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height)

    faceapi.draw.drawDetections(canvas, resizedDetections)
    faceapi.draw.drawFaceExpressions(canvas, resizedDetections)
  }, 100)
})