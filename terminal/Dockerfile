FROM alpine:3.20

# ttyd serves a browser terminal; every session starts terminal-login, which
# only runs ssh. Access to the server therefore needs a normal SSH login.
RUN apk add --no-cache ttyd openssh-client-default \
    && adduser -D -h /home/terminal terminal \
    && install -d -m 700 -o terminal -g terminal /home/terminal/.ssh

COPY --chmod=755 terminal-login.sh /usr/local/bin/terminal-login

USER terminal
WORKDIR /home/terminal

EXPOSE 7681

CMD ["ttyd", "--writable", "--port", "7681", "--base-path", "/terminal", "--check-origin", "--ping-interval", "30", "-t", "titleFixed=Server terminal", "-t", "fontSize=15", "/usr/local/bin/terminal-login"]
