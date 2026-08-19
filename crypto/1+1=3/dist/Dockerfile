FROM golang:1.21-alpine
WORKDIR /app

COPY go.mod go.sum ./
COPY challenge.go ./challenge.go
COPY flag.txt ./flag.txt
COPY vk.hex ./vk.hex
COPY pk.hex ./pk.hex

RUN go build -o challenge ./challenge.go

CMD ["./challenge"]
